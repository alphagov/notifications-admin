from datetime import timedelta

import pytz
from notifications_utils.letter_timings import (
    CANCELLABLE_JOB_LETTER_STATUSES,
    get_letter_timings,
    letter_can_be_cancelled,
)
from notifications_utils.timezones import utc_string_to_aware_gmt_datetime
from werkzeug.utils import cached_property

from app.models import JSONModel, ModelList, PaginatedModelList
from app.notify_client.job_api_client import job_api_client
from app.notify_client.notification_api_client import notification_api_client
from app.notify_client.service_api_client import service_api_client
from app.utils import is_less_than_days_ago, set_status_filters
from app.utils.letters import get_letter_printing_statement


class Job(JSONModel):

    ALLOWED_PROPERTIES = {
        'id',
        'service',
        'template_name',
        'template_version',
        'original_file_name',
        'created_at',
        'notification_count',
        'created_by',
        'template_type',
        'recipient',
    }

    @classmethod
    def from_id(cls, job_id, service_id):
        return cls(job_api_client.get_job(service_id, job_id)['data'])

    @property
    def status(self):
        return self._dict.get('job_status')

    @property
    def cancelled(self):
        return self.status == 'cancelled'

    @property
    def scheduled(self):
        return self.status == 'scheduled'

    @property
    def scheduled_for(self):
        return self._dict.get('scheduled_for')

    @property
    def upload_type(self):
        return self._dict.get('upload_type')

    @property
    def pdf_letter(self):
        return self.upload_type == 'letter'

    @property
    def processing_started(self):
        if not self._dict.get('processing_started'):
            return None
        return self._dict['processing_started']

    def _aggregate_statistics(self, *statuses):
        return sum(
            outcome['count'] for outcome in self._dict['statistics']
            if not statuses or outcome['status'] in statuses
        )

    @property
    def notifications_delivered(self):
        return self._aggregate_statistics('delivered', 'sent')

    @property
    def notifications_failed(self):
        return self._aggregate_statistics(
            'failed', 'technical-failure', 'temporary-failure',
            'permanent-failure', 'cancelled',
        )

    @property
    def notifications_requested(self):
        return self._aggregate_statistics()

    @property
    def notifications_sent(self):
        return self.notifications_delivered + self.notifications_failed

    @property
    def notifications_sending(self):
        if self.scheduled:
            return 0
        return self.notification_count - self.notifications_sent

    @property
    def notifications_created(self):
        return notification_api_client.get_notification_count_for_job_id(
            service_id=self.service, job_id=self.id
        )

    @property
    def still_processing(self):
        return (
            self.percentage_complete < 100 and self.status != 'finished'
        )

    @cached_property
    def finished_processing(self):
        return self.notification_count == self.notifications_sent

    @property
    def awaiting_processing_or_recently_processed(self):
        if not self.processing_started:
            # Assume that if processing hasn’t started yet then the job
            # must have been created recently enough to not have any
            # notifications yet
            return True
        return is_less_than_days_ago(self.processing_started, 1)

    @property
    def template_id(self):
        return self._dict['template']

    @cached_property
    def template(self):
        return service_api_client.get_service_template(
            service_id=self.service,
            template_id=self.template_id,
            version=self.template_version,
        )['data']

    @property
    def percentage_complete(self):
        return self.notifications_requested / self.notification_count * 100

    @property
    def letter_job_can_be_cancelled(self):

        if self.template['template_type'] != 'letter':
            return False

        if any(self.uncancellable_notifications):
            return False

        if not letter_can_be_cancelled(
            'created',
            utc_string_to_aware_gmt_datetime(self.created_at).replace(tzinfo=None)
        ):
            return False

        return True

    @property
    def letter_printing_statement(self):
        if self.upload_type != 'letter_day':
            raise TypeError()
        return get_letter_printing_statement(
            'created',
            # We have to make the time just before 5:30pm because a
            # letter uploaded at 5:30pm will be printed the next day
            (
                utc_string_to_aware_gmt_datetime(self.created_at) - timedelta(minutes=1)
            ).astimezone(pytz.utc).isoformat(),
            long_form=False,
        )

    @cached_property
    def all_notifications(self):
        return self.get_notifications(set_status_filters({}))['notifications']

    @property
    def uncancellable_notifications(self):
        return (
            n for n in self.all_notifications
            if n['status'] not in CANCELLABLE_JOB_LETTER_STATUSES
        )

    @cached_property
    def postage(self):
        # There might be no notifications if the job has only just been
        # created and the tasks haven't run yet
        try:
            return self.all_notifications[0]['postage']
        except IndexError:
            return self.template['postage']

    @property
    def letter_timings(self):
        return get_letter_timings(self.created_at, postage=self.postage)

    @property
    def failure_rate(self):
        if not self.notifications_delivered:
            return 100 if self.notifications_failed else 0
        return (
            self.notifications_failed / (
                self.notifications_failed + self.notifications_delivered
            ) * 100
        )

    @property
    def high_failure_rate(self):
        return self.failure_rate > 30

    def get_notifications(self, status):
        return notification_api_client.get_notifications_for_service(
            self.service, self.id, status=status,
        )

    def cancel(self):
        if self.template_type == 'letter':
            return job_api_client.cancel_letter_job(self.service, self.id)
        else:
            return job_api_client.cancel_job(self.service, self.id)


class ImmediateJobs(ModelList):
    client_method = job_api_client.get_immediate_jobs
    model = Job


class ScheduledJobs(ImmediateJobs):
    client_method = job_api_client.get_scheduled_jobs


class PaginatedJobs(PaginatedModelList, ImmediateJobs):
    client_method = job_api_client.get_page_of_jobs
    statuses = None

    def __init__(self, service_id, *, contact_list_id=None, page=None, limit_days=None):
        super().__init__(
            service_id,
            contact_list_id=contact_list_id,
            statuses=self.statuses,
            page=page,
            limit_days=limit_days,
        )


class PaginatedJobsAndScheduledJobs(PaginatedJobs):
    statuses = job_api_client.NON_CANCELLED_JOB_STATUSES


class PaginatedUploads(PaginatedModelList, ImmediateJobs):
    client_method = job_api_client.get_uploads

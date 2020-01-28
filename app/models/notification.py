from datetime import datetime

from app.models import JSONModel, ModelList
from app.notify_client.api_key_api_client import KEY_TYPE_TEST
from app.notify_client.notification_api_client import notification_api_client
from notifications_utils.timezones import utc_string_to_aware_gmt_datetime
from app.utils import DELIVERED_STATUSES, FAILURE_STATUSES, SENDING_STATUSES
from werkzeug.utils import cached_property


class Notification(JSONModel):

    ALLOWED_PROPERTIES = {
        'id',
        'to',
        'template',
        'status',
        'created_by',
        'job_row_number',
        'service',
        'template_version',
        'personalisation',
        'postage',
        'notification_type',
        'reply_to_text',
        'client_reference',
        'created_by_name',
        'recipient',
        'template_name',
        'template_type',
        'created_by_email_address',
        'job_name',
    }

    DATETIME_PROPERTIES = {
        'sent_at',
        'created_at',
        'updated_at',
    }

    @classmethod
    def from_id(cls, notification_id, service_id):
        return cls(notification_api_client.get_notification(service_id, notification_id))

    @property
    def postage(self):
        return self._dict.get('postage')

    @property
    def key_type(self):
        return self._dict.get('key_type')

    @property
    def created_by(self):
        return self._dict.get('created_by')

    @property
    def all_personalisation(self):

        out = {}

        if not self.template.get('redact_personalisation'):
            out.update(self.personalisation)

        if self.template['template_type'] == 'email':
            out.update(email_address=self.to)

        if self.template['template_type'] == 'sms':
            out.update(phone_number=self.to)

        return out

    @property
    def sending(self):
        return self.status in SENDING_STATUSES

    @property
    def finished(self):
        return self.delivered or self.failed

    @property
    def delivered(self):
        return self.status in DELIVERED_STATUSES

    @property
    def failed(self):
        return self.status in FAILURE_STATUSES

    @property
    def sent_with_test_key(self):
        return self.key_type == KEY_TYPE_TEST

    @property
    def is_precompiled_letter(self):
        return self.template['is_precompiled_letter']

    @cached_property
    def job(self):
        from app.models.job import Job
        if self._dict['job']:
            return Job.from_id(self._dict['job']['id'], service_id=self.service_id)
        return None

    @property
    def seconds_since_sending(self):
        return (
            utc_string_to_aware_gmt_datetime(datetime.utcnow().isoformat()) -
            self.created_at
        ).seconds

    def delivered_within(self, seconds):
        if self.failed:
            return False
        if self.sending and self.seconds_since_sending > seconds:
            return False
        return True

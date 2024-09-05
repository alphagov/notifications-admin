from flask import abort
from notifications_utils.timezones import utc_string_to_aware_gmt_datetime

from app.formatters import format_date_human, format_datetime_human
from app.models import JSONModel, ModelList
from app.notify_client.service_api_client import service_api_client
from app.utils.time import to_utc_string


class UnsubscribeRequestsReport(JSONModel):
    ALLOWED_PROPERTIES = {
        "count",
        "batch_id",
        "is_a_batched_report",
    }
    __sort_attribute__ = "earliest_timestamp"

    @property
    def status(self):
        if not self.is_a_batched_report:
            return "Not downloaded"
        if not self.processed_by_service_at:
            return "Downloaded"
        return "Completed"

    @property
    def completed(self):
        return self.processed_by_service_at is not None

    @property
    def will_be_archived_at(self):
        return utc_string_to_aware_gmt_datetime(self._dict["will_be_archived_at"])

    @property
    def earliest_timestamp(self):
        return utc_string_to_aware_gmt_datetime(self._dict["earliest_timestamp"])

    @property
    def latest_timestamp(self):
        return utc_string_to_aware_gmt_datetime(self._dict["latest_timestamp"])

    @property
    def processed_by_service_at(self):
        if not self._dict["processed_by_service_at"]:
            return None
        return utc_string_to_aware_gmt_datetime(self._dict["processed_by_service_at"])

    @property
    def other_reports(self):
        return (report for report in self.all_reports if report.batch_id != self.batch_id)

    @property
    def other_reports_starting_the_same_day(self):
        return (
            other for other in self.other_reports if other.earliest_timestamp.date() == self.earliest_timestamp.date()
        )

    @property
    def is_first_of_several_reports_on_the_same_day(self):
        return any(self.other_reports_starting_the_same_day) and all(
            self.earliest_timestamp < other.earliest_timestamp for other in self.other_reports_starting_the_same_day
        )

    @property
    def starts_on_a_day_another_report_ends(self):
        return self.earliest_timestamp.date() in {other.latest_timestamp.date() for other in self.other_reports}

    @property
    def ends_on_a_day_another_report_starts(self):
        return self.latest_timestamp.date() in {other.earliest_timestamp.date() for other in self.other_reports}

    @property
    def earliest(self):
        if self.is_first_of_several_reports_on_the_same_day:
            # Don’t show separate start time
            return self.latest

        if self.starts_on_a_day_another_report_ends:
            return format_datetime_human(self.earliest_timestamp, date_prefix="")

        return format_date_human(self.earliest_timestamp)

    @property
    def latest(self):
        if self.is_first_of_several_reports_on_the_same_day:
            return format_datetime_human(self.latest_timestamp, date_prefix="", separator="until")

        if self.starts_on_a_day_another_report_ends or self.ends_on_a_day_another_report_starts:
            return format_datetime_human(self.latest_timestamp, date_prefix="")

        return format_date_human(self.latest_timestamp)

    @property
    def title(self):
        if self.earliest == self.latest:
            return self.latest

        return f"{self.earliest} to {self.latest}"


class UnsubscribeRequestsReports(ModelList):
    client_method = service_api_client.get_unsubscribe_reports_summary
    model = UnsubscribeRequestsReport

    def __getitem__(self, index):
        instance = super().__getitem__(index)
        instance.all_reports = self
        return instance

    def get_by_batch_id(self, batch_id):
        for report in self:
            if report.batch_id == batch_id:
                return report
        abort(404)

    def get_unbatched_report(self):
        for report in self:
            if not report.is_a_batched_report:
                return report
        abort(404)

    def batch_unbatched(self, service_id):
        unbatched = self.get_unbatched_report()
        created = service_api_client.create_unsubscribe_request_report(
            service_id,
            {
                "count": unbatched.count,
                "earliest_timestamp": to_utc_string(unbatched.earliest_timestamp),
                "latest_timestamp": to_utc_string(unbatched.latest_timestamp),
            },
        )
        return created["report_id"]

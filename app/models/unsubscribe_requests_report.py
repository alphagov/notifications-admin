from datetime import datetime
from typing import Any

from flask import abort

from app.formatters import format_date_human, format_time, get_human_day
from app.models import JSONModel, ModelList
from app.notify_client.service_api_client import service_api_client
from app.utils.time import to_utc_string


class UnsubscribeRequestsReport(JSONModel):
    service_id: Any
    count: int
    batch_id: Any
    is_a_batched_report: bool
    will_be_archived_at: datetime
    earliest_timestamp: datetime
    latest_timestamp: datetime
    processed_by_service_at: datetime

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
            return (get_human_day(self.earliest_timestamp), " at ", format_time(self.earliest_timestamp))

        return (format_date_human(self.earliest_timestamp), "", "")

    @property
    def latest(self):
        if self.is_first_of_several_reports_on_the_same_day:
            return (
                get_human_day(self.latest_timestamp),
                " at " if self.count == 1 else " until ",
                format_time(self.latest_timestamp),
            )

        if self.starts_on_a_day_another_report_ends or self.ends_on_a_day_another_report_starts:
            return (get_human_day(self.latest_timestamp), " at ", format_time(self.latest_timestamp))

        return (format_date_human(self.latest_timestamp), "", "")

    @property
    def title(self):
        if self.earliest == self.latest:
            return "".join(self.latest)

        if self.earliest[0] == self.latest[0]:
            return f"{self.earliest[0]} from {self.earliest[-1]} to {self.latest[-1]}"

        return "".join(self.earliest + (" to ",) + self.latest)


class UnsubscribeRequestsReports(ModelList):
    model = UnsubscribeRequestsReport

    @staticmethod
    def _get_items(*args, **kwargs):
        return service_api_client.get_unsubscribe_reports_summary(*args, **kwargs)

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

    def batch_unbatched(self):
        unbatched = self.get_unbatched_report()
        created = service_api_client.create_unsubscribe_request_report(
            unbatched.service_id,
            {
                "count": unbatched.count,
                "earliest_timestamp": to_utc_string(unbatched.earliest_timestamp),
                "latest_timestamp": to_utc_string(unbatched.latest_timestamp),
            },
        )
        return created["report_id"]

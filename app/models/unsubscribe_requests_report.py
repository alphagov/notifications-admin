from datetime import timedelta

from flask import abort
from notifications_utils.timezones import utc_string_to_aware_gmt_datetime

from app.models import JSONModel, ModelList
from app.notify_client.service_api_client import service_api_client


class UnsubscribeRequestsReport(JSONModel):
    ALLOWED_PROPERTIES = {
        "count",
        "earliest_timestamp",
        "latest_timestamp",
        "processed_by_service_at",
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
    def report_latest_download_date(self):
        if self.status == "Completed":
            limit = 7
            starting_date = self.processed_by_service_at
        else:
            limit = 90
            starting_date = self.latest_timestamp
        return utc_string_to_aware_gmt_datetime(starting_date) + timedelta(days=limit)


class UnsubscribeRequestsReports(ModelList):
    client_method = service_api_client.get_unsubscribe_reports_summary
    model = UnsubscribeRequestsReport

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

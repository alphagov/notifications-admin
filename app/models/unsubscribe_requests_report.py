from flask import abort

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
        "status",
    }
    __sort_attribute__ = "earliest_timestamp"


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

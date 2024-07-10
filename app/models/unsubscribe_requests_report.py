from app.models import JSONModel


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

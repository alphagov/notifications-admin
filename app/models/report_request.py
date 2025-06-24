from datetime import datetime
from typing import Any

from flask import current_app
from notifications_utils.s3 import s3download

from app import report_request_api_client
from app.models import JSONModel
from app.s3_client import check_s3_object_exists


class ReportRequest(JSONModel):
    id: Any
    user_id: Any
    service_id: Any
    report_type: str
    status: str
    parameter: Any
    created_at: datetime
    updated_at: datetime

    __sort_attribute__ = "created_at"

    @classmethod
    def from_id(cls, service_id, report_request_id):
        return cls(report_request_api_client.get_report_request(service_id, report_request_id)["data"])

    @staticmethod
    def get_bucket_name():
        return current_app.config["S3_BUCKET_REPORT_REQUESTS_DOWNLOAD"]

    @staticmethod
    def download(report_request_id):
        return s3download(
            bucket_name=ReportRequest.get_bucket_name(),
            filename=f"notifications_report/{report_request_id}.csv",
        )

    @staticmethod
    def exists_in_s3(report_request_id):
        return check_s3_object_exists(
            bucket_name=ReportRequest.get_bucket_name(),
            filename=f"notifications_report/{report_request_id}.csv",
        )

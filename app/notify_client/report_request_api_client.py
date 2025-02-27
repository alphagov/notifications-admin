from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient


class ReportRequestClient(NotifyAdminAPIClient):
    def get_report_request(self, service_id, report_request_id):
        report_request = self.get(url=f"/service/{service_id}/report-request/{report_request_id}")

        return report_request


_report_request_api_client_context_var: ContextVar[ReportRequestClient] = ContextVar("report_request_api_client")
get_report_request_api_client: LazyLocalGetter[ReportRequestClient] = LazyLocalGetter(
    _report_request_api_client_context_var,
    lambda: ReportRequestClient(current_app),
)
memo_resetters.append(lambda: get_report_request_api_client.clear())
report_request_api_client = LocalProxy(get_report_request_api_client)

from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, api_client_request_session


class ComplaintApiClient(NotifyAdminAPIClient):
    def get_all_complaints(self, page=1):
        params = {"page": page}
        return self.get("/complaint", params=params)

    def get_complaint_count(self, params_dict=None):
        return self.get("/complaint/count-by-date-range", params=params_dict)


_complaint_api_client_context_var: ContextVar[ComplaintApiClient] = ContextVar("complaint_api_client")
get_complaint_api_client: LazyLocalGetter[ComplaintApiClient] = LazyLocalGetter(
    _complaint_api_client_context_var,
    lambda: ComplaintApiClient(current_app, request_session=api_client_request_session),
)
memo_resetters.append(lambda: get_complaint_api_client.clear())
complaint_api_client = LocalProxy(get_complaint_api_client)

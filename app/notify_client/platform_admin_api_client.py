from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient


class AdminApiClient(NotifyAdminAPIClient):
    """API client for looking up arbitrary API objects based on incomplete information, eg just a UUID"""

    def find_by_uuid(self, uuid_):
        return self.post(url="/platform-admin/find-by-uuid", data={"uuid": uuid_})


_admin_api_client_context_var: ContextVar[AdminApiClient] = ContextVar("admin_api_client")
get_admin_api_client: LazyLocalGetter[AdminApiClient] = LazyLocalGetter(
    _admin_api_client_context_var,
    lambda: AdminApiClient(current_app),
)
memo_resetters.append(lambda: get_admin_api_client.clear())
admin_api_client = LocalProxy(get_admin_api_client)

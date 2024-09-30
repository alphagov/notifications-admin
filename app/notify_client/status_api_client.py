from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, cache


class StatusApiClient(NotifyAdminAPIClient):
    def get_status(self, *params):
        return self.get("/_status", *params)

    @cache.set("live-service-and-organisation-counts", ttl_in_seconds=3600)
    def get_count_of_live_services_and_organisations(self):
        return self.get("/_status/live-service-and-organisation-counts")


_status_api_client_context_var: ContextVar[StatusApiClient] = ContextVar("status_api_client")
get_status_api_client: LazyLocalGetter[StatusApiClient] = LazyLocalGetter(
    _status_api_client_context_var,
    lambda: StatusApiClient(current_app),
)
memo_resetters.append(lambda: get_status_api_client.clear())
status_api_client = LocalProxy(get_status_api_client)

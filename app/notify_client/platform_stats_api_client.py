from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient


class PlatformStatsAPIClient(NotifyAdminAPIClient):
    def get_aggregate_platform_stats(self, params_dict=None):
        return self.get("/platform-stats", params=params_dict)


_platform_stats_api_client_context_var: ContextVar[PlatformStatsAPIClient] = ContextVar("platform_stats_api_client")
get_platform_stats_api_client: LazyLocalGetter[PlatformStatsAPIClient] = LazyLocalGetter(
    _platform_stats_api_client_context_var,
    lambda: PlatformStatsAPIClient(current_app),
)
memo_resetters.append(lambda: get_platform_stats_api_client.clear())
platform_stats_api_client = LocalProxy(get_platform_stats_api_client)

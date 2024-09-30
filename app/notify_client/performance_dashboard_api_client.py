from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, cache


class PerformanceDashboardAPIClient(NotifyAdminAPIClient):
    @cache.set("performance-stats-{start_date}-to-{end_date}", ttl_in_seconds=3600)
    def get_performance_dashboard_stats(
        self,
        *,
        start_date,
        end_date,
    ):
        return self.get(
            "/performance-dashboard",
            params={
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )


_performance_dashboard_api_client_context_var: ContextVar[PerformanceDashboardAPIClient] = ContextVar(
    "performance_dashboard_api_client"
)
get_performance_dashboard_api_client: LazyLocalGetter[PerformanceDashboardAPIClient] = LazyLocalGetter(
    _performance_dashboard_api_client_context_var,
    lambda: PerformanceDashboardAPIClient(current_app),
)
memo_resetters.append(lambda: get_performance_dashboard_api_client.clear())
performance_dashboard_api_client = LocalProxy(get_performance_dashboard_api_client)

from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, api_client_request_session


class TemplateStatisticsApiClient(NotifyAdminAPIClient):
    def get_template_statistics_for_service(self, service_id, limit_days=None):
        params = {}
        if limit_days is not None:
            params["limit_days"] = limit_days

        return self.get(url=f"/service/{service_id}/template-statistics", params=params)["data"]

    def get_monthly_template_usage_for_service(self, service_id, year):
        return self.get(url=f"/service/{service_id}/notifications/templates_usage/monthly?year={year}")["stats"]

    def get_last_used_date_for_template(self, service_id, template_id):
        return self.get(url=f"/service/{service_id}/template-statistics/last-used/{template_id}")["last_date_used"]


_template_statistics_client_context_var: ContextVar[TemplateStatisticsApiClient] = ContextVar(
    "template_statistics_client"
)
get_template_statistics_client: LazyLocalGetter[TemplateStatisticsApiClient] = LazyLocalGetter(
    _template_statistics_client_context_var,
    lambda: TemplateStatisticsApiClient(current_app, request_session=api_client_request_session),
)
memo_resetters.append(lambda: get_template_statistics_client.clear())
template_statistics_client = LocalProxy(get_template_statistics_client)

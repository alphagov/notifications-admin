from app.notify_client import NotifyAdminAPIClient


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


template_statistics_client = TemplateStatisticsApiClient()

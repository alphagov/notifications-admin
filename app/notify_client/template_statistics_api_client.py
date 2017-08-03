from app.notify_client import NotifyAdminAPIClient


class TemplateStatisticsApiClient(NotifyAdminAPIClient):
    def __init__(self):
        super().__init__("a" * 73, "b")

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.service_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.api_key = app.config['ADMIN_CLIENT_SECRET']

    def get_template_statistics_for_service(self, service_id, limit_days=None):
        params = {}
        if limit_days is not None:
            params['limit_days'] = limit_days

        return self.get(
            url='/service/{}/template-statistics'.format(service_id),
            params=params
        )['data']

    def get_monthly_template_statistics_for_service(self, service_id, year):

        return self.get(
            url='/service/{}/notifications/templates/monthly?year={}'.format(service_id, year)
        )['data']

    def get_template_statistics_for_template(self, service_id, template_id):

        return self.get(
            url='/service/{}/template-statistics/{}'.format(service_id, template_id)
        )['data']

from notifications_python_client.base import BaseAPIClient


class TemplateStatisticsApiClient(BaseAPIClient):
    def __init__(self):
        super().__init__("a", "b", "c")

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

    def get_template_statistics_for_template(self, service_id, template_id):

        return self.get(
            url='/service/{}/template-statistics/{}'.format(service_id, template_id)
        )['data']

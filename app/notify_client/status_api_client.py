from notifications_python_client.base import BaseAPIClient


class StatusApiClient(BaseAPIClient):
    def __init__(self):
        super().__init__("a", "b", "c")

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.service_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.api_key = app.config['ADMIN_CLIENT_SECRET']

    def get_status(self, *params):
        return self.get(url='/_status', *params)

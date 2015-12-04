from __future__ import unicode_literals
from notify_client import NotifyAPIClient


class AdminAPIClient(NotifyAPIClient):
    def init_app(self, app):
        self.base_url = app.config['NOTIFY_DATA_API_URL']
        self.auth_token = app.config['NOTIFY_DATA_API_AUTH_TOKEN']

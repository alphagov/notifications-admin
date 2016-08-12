from notifications_python_client.base import BaseAPIClient
from app.notify_client import _attach_current_user


class ProviderClient(BaseAPIClient):
    def __init__(self, base_url=None, client_id=None, secret=None):
        super(self.__class__, self).__init__(
            base_url=base_url or 'base_url',
            client_id=client_id or 'client_id',
            secret=secret or 'secret'
        )

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.client_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.secret = app.config['ADMIN_CLIENT_SECRET']

    def get_all_providers(self):
        return self.get(
            url='/provider-details'
        )

    def get_provider_by_id(self, provider_id):
        return self.get(
            url='/provider-details/{}'.format(provider_id)
        )

    def update_provider(self, provider_id, priority):
        data = {
            "priority": priority
        }
        data = _attach_current_user(data)
        return self.post(url='/provider-details/{}'.format(provider_id), data=data)

from notifications_python_client.base import BaseAPIClient
from app.notify_client import _attach_current_user


# must match key types in notifications-api/app/models.py
KEY_TYPE_NORMAL = 'normal'
KEY_TYPE_TEAM = 'team'


class ApiKeyApiClient(BaseAPIClient):
    def __init__(self, base_url=None, client_id=None, secret=None):
        super(self.__class__, self).__init__(base_url=base_url or 'base_url',
                                             client_id=client_id or 'client_id',
                                             secret=secret or 'secret')

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.client_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.secret = app.config['ADMIN_CLIENT_SECRET']

    def get_api_keys(self, service_id, key_id=None):
        if key_id:
            return self.get(url='/service/{}/api-keys/{}'.format(service_id, key_id))
        else:
            return self.get(url='/service/{}/api-keys'.format(service_id))

    def create_api_key(self, service_id, key_name):
        data = {
            'name': key_name,
            'key_type': KEY_TYPE_NORMAL
        }
        _attach_current_user(data)
        key = self.post(url='/service/{}/api-key'.format(service_id), data=data)
        return key['data']

    def revoke_api_key(self, service_id, key_id):
        data = _attach_current_user({})
        return self.post(
            url='/service/{0}/api-key/revoke/{1}'.format(service_id, key_id),
            data=data)

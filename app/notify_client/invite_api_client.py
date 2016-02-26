
from notifications_python_client.base import BaseAPIClient


class InviteApiClient(BaseAPIClient):
    def __init__(self, base_url=None, client_id=None, secret=None):
        super(self.__class__, self).__init__(base_url=base_url or 'base_url',
                                             client_id=client_id or 'client_id',
                                             secret=secret or 'secret')

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.client_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.secret = app.config['ADMIN_CLIENT_SECRET']

    def create_invite(self, invite_from_id, service_id, email_address):
        data = {
            'service': str(service_id),
            'email_address': email_address,
            'from_user': invite_from_id
        }
        resp = self.post(url='/service/{}/invite'.format(service_id), data=data)
        return resp['data']

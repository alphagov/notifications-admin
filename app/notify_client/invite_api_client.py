
from notifications_python_client.base import BaseAPIClient
from app.notify_client.models import User


class InviteApiClient(BaseAPIClient):
    def __init__(self, base_url=None, client_id=None, secret=None):
        super(self.__class__, self).__init__(base_url=base_url or 'base_url',
                                             client_id=client_id or 'client_id',
                                             secret=secret or 'secret')

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.client_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.secret = app.config['ADMIN_CLIENT_SECRET']

    def create_invite(self, invite_from_id, service_id, email_address, permissions):
        data = {
            'service': str(service_id),
            'email_address': email_address,
            'from_user': invite_from_id,
            'permissions': permissions
        }
        resp = self.post(url='/service/{}/invite'.format(service_id), data=data)
        return resp['data']

    def get_invites_for_service(self, service_id):
        endpoint = '/service/{}/invite'.format(service_id)
        resp = self.get(endpoint)
        return [User(data) for data in resp['data']]

    def cancel_invited_user(self, service_id, invited_user_id):
        data = {'status': 'cancelled'}
        resp = self.post(url='/service/{0}/invite/{0}'.format(service_id, invited_user_id),
                         data = data)
        return resp['data']
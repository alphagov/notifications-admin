from app.models.user import (
    InvitedUser,
    translate_permissions_from_admin_roles_to_db,
)
from app.notify_client import NotifyAdminAPIClient, _attach_current_user, cache


class InviteApiClient(NotifyAdminAPIClient):

    def init_app(self, app):
        super().init_app(app)

        self.admin_url = app.config['ADMIN_BASE_URL']

    def create_invite(self,
                      invite_from_id,
                      service_id,
                      email_address,
                      permissions,
                      auth_type,
                      folder_permissions):
        data = {
            'service': str(service_id),
            'email_address': email_address,
            'from_user': invite_from_id,
            'permissions': ','.join(sorted(translate_permissions_from_admin_roles_to_db(permissions))),
            'auth_type': auth_type,
            'invite_link_host': self.admin_url,
            'folder_permissions': folder_permissions,
        }
        data = _attach_current_user(data)
        resp = self.post(url='/service/{}/invite'.format(service_id), data=data)
        return InvitedUser(**resp['data'])

    def get_invites_for_service(self, service_id):
        return [
            InvitedUser(**invite)
            for invite in self._get_invites_for_service(service_id)
            if invite['status'] != 'accepted'
        ]

    def _get_invites_for_service(self, service_id):
        return self.get(
            '/service/{}/invite'.format(service_id)
        )['data']

    def check_token(self, token):
        resp = self.get(url='/invite/service/{}'.format(token))
        return InvitedUser(**resp['data'])

    def cancel_invited_user(self, service_id, invited_user_id):
        data = {'status': 'cancelled'}
        data = _attach_current_user(data)
        self.post(url='/service/{0}/invite/{1}'.format(service_id, invited_user_id),
                  data=data)

    @cache.delete('service-{service_id}')
    @cache.delete('user-{invited_user_id}')
    def accept_invite(self, service_id, invited_user_id):
        data = {'status': 'accepted'}
        self.post(url='/service/{0}/invite/{1}'.format(service_id, invited_user_id),
                  data=data)


invite_api_client = InviteApiClient()

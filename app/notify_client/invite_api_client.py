from app.notify_client import NotifyAdminAPIClient, _attach_current_user, cache
from app.utils.user_permissions import (
    all_ui_permissions,
    translate_permissions_from_ui_to_db,
)


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
            'service': service_id,
            'email_address': email_address,
            'from_user': invite_from_id,
            'permissions': ','.join(sorted(translate_permissions_from_ui_to_db(permissions))),
            'auth_type': auth_type,
            'invite_link_host': self.admin_url,
            'folder_permissions': folder_permissions,
        }
        data = _attach_current_user(data)
        resp = self.post(url='/service/{}/invite'.format(service_id), data=data)
        return resp['data']

    def get_invites_for_service(self, service_id):
        return self.get(
            '/service/{}/invite'.format(service_id)
        )['data']

    def get_invited_user(self, invited_user_id):
        return self.get(
            f'/invite/service/{invited_user_id}'
        )['data']

    def get_invited_user_for_service(self, service_id, invited_user_id):
        return self.get(
            f'/service/{service_id}/invite/{invited_user_id}'
        )['data']

    def get_count_of_invites_with_permission(self, service_id, permission):
        if permission not in all_ui_permissions:
            raise TypeError('{} is not a valid permission'.format(permission))
        return len([
            invited_user for invited_user in self.get_invites_for_service(service_id)
            if invited_user.has_permission_for_service(service_id, permission)
        ])

    def check_token(self, token):
        return self.get(url='/invite/service/check/{}'.format(token))['data']

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

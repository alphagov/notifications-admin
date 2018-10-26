from app.notify_client import NotifyAdminAPIClient, _attach_current_user
from app.notify_client.models import InvitedOrgUser


class OrgInviteApiClient(NotifyAdminAPIClient):
    def __init__(self):
        super().__init__("a" * 73, "b")

    def init_app(self, app):
        super().init_app(app)

        self.admin_url = app.config['ADMIN_BASE_URL']

    def create_invite(self, invite_from_id, org_id, email_address):
        data = {
            'email_address': email_address,
            'invited_by': invite_from_id,
            'invite_link_host': self.admin_url,
        }
        data = _attach_current_user(data)
        resp = self.post(url='/organisation/{}/invite'.format(org_id), data=data)
        return InvitedOrgUser(**resp['data'])

    def get_invites_for_organisation(self, org_id):
        endpoint = '/organisation/{}/invite'.format(org_id)
        resp = self.get(endpoint)
        invites = resp['data']
        invited_users = self._get_invited_org_users(invites)
        return invited_users

    def check_token(self, token):
        resp = self.get(url='/invite/organisation/{}'.format(token))
        return InvitedOrgUser(**resp['data'])

    def cancel_invited_user(self, org_id, invited_user_id):
        data = {'status': 'cancelled'}
        data = _attach_current_user(data)
        self.post(url='/organisation/{0}/invite/{1}'.format(org_id, invited_user_id),
                  data=data)

    def accept_invite(self, org_id, invited_user_id):
        data = {'status': 'accepted'}
        self.post(url='/organisation/{0}/invite/{1}'.format(org_id, invited_user_id),
                  data=data)

    def _get_invited_org_users(self, invites):
        invited_users = []
        for invite in invites:
            invited_user = InvitedOrgUser(**invite)
            invited_users.append(invited_user)
        return invited_users


org_invite_api_client = OrgInviteApiClient()

from app.notify_client import NotifyAdminAPIClient, _attach_current_user


class OrgInviteApiClient(NotifyAdminAPIClient):

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
        return resp['data']

    def get_invites_for_organisation(self, org_id):
        endpoint = '/organisation/{}/invite'.format(org_id)
        resp = self.get(endpoint)
        return resp['data']

    def get_invited_user_for_org(self, org_id, invited_org_user_id):
        return self.get(
            f'/organisation/{org_id}/invite/{invited_org_user_id}'
        )['data']

    def get_invited_user(self, invited_user_id):
        return self.get(
            f'/invite/organisation/{invited_user_id}'
        )['data']

    def check_token(self, token):
        resp = self.get(url='/invite/organisation/check/{}'.format(token))
        return resp['data']

    def cancel_invited_user(self, org_id, invited_user_id):
        data = {'status': 'cancelled'}
        data = _attach_current_user(data)
        self.post(url='/organisation/{0}/invite/{1}'.format(org_id, invited_user_id),
                  data=data)

    def accept_invite(self, org_id, invited_user_id):
        data = {'status': 'accepted'}
        self.post(url='/organisation/{0}/invite/{1}'.format(org_id, invited_user_id),
                  data=data)


org_invite_api_client = OrgInviteApiClient()

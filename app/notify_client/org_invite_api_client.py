from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, _attach_current_user


class OrgInviteApiClient(NotifyAdminAPIClient):
    def __init__(self, app):
        super().__init__(app)

        self.admin_url = app.config["ADMIN_BASE_URL"]

    def create_invite(self, invite_from_id, org_id, email_address, permissions: list[str]):
        data = {
            "email_address": email_address,
            "invited_by": invite_from_id,
            "invite_link_host": self.admin_url,
            "permissions": permissions,
        }
        data = _attach_current_user(data)
        resp = self.post(url=f"/organisation/{org_id}/invite", data=data)
        return resp["data"]

    def get_invites_for_organisation(self, org_id):
        endpoint = f"/organisation/{org_id}/invite"
        resp = self.get(endpoint)
        return resp["data"]

    def get_invited_user_for_org(self, org_id, invited_org_user_id):
        return self.get(f"/organisation/{org_id}/invite/{invited_org_user_id}")["data"]

    def get_invited_user(self, invited_user_id):
        return self.get(f"/invite/organisation/{invited_user_id}")["data"]

    def check_token(self, token):
        resp = self.get(url=f"/invite/organisation/check/{token}")
        return resp["data"]

    def cancel_invited_user(self, org_id, invited_user_id):
        data = {"status": "cancelled"}
        data = _attach_current_user(data)
        self.post(url=f"/organisation/{org_id}/invite/{invited_user_id}", data=data)

    def accept_invite(self, org_id, invited_user_id):
        data = {"status": "accepted"}
        self.post(url=f"/organisation/{org_id}/invite/{invited_user_id}", data=data)


_org_invite_api_client_context_var: ContextVar[OrgInviteApiClient] = ContextVar("org_invite_api_client")
get_org_invite_api_client: LazyLocalGetter[OrgInviteApiClient] = LazyLocalGetter(
    _org_invite_api_client_context_var,
    lambda: OrgInviteApiClient(current_app),
)
memo_resetters.append(lambda: get_org_invite_api_client.clear())
org_invite_api_client = LocalProxy(get_org_invite_api_client)

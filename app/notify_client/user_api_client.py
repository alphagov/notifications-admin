from contextvars import ContextVar

from flask import current_app
from notifications_python_client.errors import HTTPError
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, cache
from app.utils.user_permissions import translate_permissions_from_ui_to_db

ALLOWED_ATTRIBUTES = {
    "name",
    "email_address",
    "mobile_number",
    "auth_type",
    "updated_by",
    "current_session_id",
    "email_access_validated_at",
    "take_part_in_research",
    "receives_new_features_email",
    "platform_admin",
}


class UserApiClient(NotifyAdminAPIClient):
    def __init__(self, app):
        super().__init__(app)

        self.admin_url = app.config["ADMIN_BASE_URL"]

    def register_user(self, name, email_address, mobile_number, password, auth_type):
        data = {
            "name": name,
            "email_address": email_address,
            "mobile_number": mobile_number,
            "password": password,
            "auth_type": auth_type,
        }
        user_data = self.post("/user", data)
        return user_data["data"]

    def get_user(self, user_id):
        return self._get_user(user_id)["data"]

    @cache.set("user-{user_id}")
    def _get_user(self, user_id):
        return self.get(f"/user/{user_id}")

    def get_user_by_email(self, email_address):
        user_data = self.post("/user/email", data={"email": email_address})
        return user_data["data"]

    def get_user_by_email_or_none(self, email_address):
        try:
            return self.get_user_by_email(email_address)
        except HTTPError as e:
            if e.status_code == 404:
                return None
            raise e

    @cache.delete("user-{user_id}")
    def update_user_attribute(self, user_id, **kwargs):
        data = dict(kwargs)
        disallowed_attributes = set(data.keys()) - ALLOWED_ATTRIBUTES
        if disallowed_attributes:
            raise TypeError(f"Not allowed to update user attributes: {', '.join(disallowed_attributes)}")

        if "platform_admin" in data and data["platform_admin"] is not False:
            raise TypeError(f"Not allowed to update user attribute platform_admin to {data['platform_admin']}")

        url = f"/user/{user_id}"
        user_data = self.post(url, data=data)
        return user_data["data"]

    @cache.delete("user-{user_id}")
    def archive_user(self, user_id):
        return self.post(f"/user/{user_id}/archive", data=None)

    @cache.delete("user-{user_id}")
    def reset_failed_login_count(self, user_id):
        url = f"/user/{user_id}/reset-failed-login-count"
        user_data = self.post(url, data={})
        return user_data["data"]

    @cache.delete("user-{user_id}")
    def update_password(self, user_id, password):
        data = {"_password": password}
        url = f"/user/{user_id}/update-password"
        user_data = self.post(url, data=data)
        return user_data["data"]

    @cache.delete("user-{user_id}")
    def verify_password(self, user_id, password):
        try:
            url = f"/user/{user_id}/verify/password"
            data = {"password": password}
            self.post(url, data=data)
            return True
        except HTTPError as e:
            if e.status_code == 400 or e.status_code == 404:
                return False

    def send_verify_code(self, user_id, code_type, to, next_string=None):
        data = {"to": to}
        if next_string:
            data["next"] = next_string
        if code_type == "email":
            data["email_auth_link_host"] = self.admin_url
        endpoint = f"/user/{user_id}/{code_type}-code"
        self.post(endpoint, data=data)

    def send_verify_email(self, user_id, to):
        data = {
            "to": to,
            "admin_base_url": self.admin_url,
        }
        endpoint = f"/user/{user_id}/email-verification"
        self.post(endpoint, data=data)

    def send_already_registered_email(self, user_id, to):
        data = {"email": to}
        endpoint = f"/user/{user_id}/email-already-registered"
        self.post(endpoint, data=data)

    @cache.delete("user-{user_id}")
    def check_verify_code(self, user_id, code, code_type):
        data = {"code_type": code_type, "code": code}
        endpoint = f"/user/{user_id}/verify/code"
        try:
            self.post(endpoint, data=data)
            return True, ""
        except HTTPError as e:
            if e.status_code == 400 or e.status_code == 404:
                return False, e.message
            raise e

    @cache.delete("user-{user_id}")
    def complete_webauthn_login_attempt(self, user_id, is_successful, webauthn_credential_id):
        data = {"successful": is_successful, "webauthn_credential_id": webauthn_credential_id}
        endpoint = f"/user/{user_id}/complete/webauthn-login"
        try:
            self.post(endpoint, data=data)
            return True, ""
        except HTTPError as e:
            if e.status_code == 403:
                return False, e.message
            raise e

    def get_users_for_service(self, service_id):
        endpoint = f"/service/{service_id}/users"
        return self.get(endpoint)["data"]

    def get_users_for_organisation(self, org_id):
        endpoint = f"/organisations/{org_id}/users"
        return self.get(endpoint)["data"]

    @cache.delete("service-{service_id}")
    @cache.delete("service-{service_id}-template-folders")
    @cache.delete("user-{user_id}")
    def add_user_to_service(self, service_id, user_id, permissions, folder_permissions):
        # permissions passed in are the combined UI permissions, not DB permissions
        endpoint = f"/service/{service_id}/users/{user_id}"
        data = {
            "permissions": [{"permission": x} for x in translate_permissions_from_ui_to_db(permissions)],
            "folder_permissions": folder_permissions,
        }

        self.post(endpoint, data=data)

    @cache.delete("user-{user_id}")
    def add_user_to_organisation(self, org_id, user_id, permissions: list[str]):
        resp = self.post(
            f"/organisations/{org_id}/users/{user_id}", data={"permissions": [{"permission": p} for p in permissions]}
        )
        return resp["data"]

    @cache.delete("service-{service_id}-template-folders")
    @cache.delete("user-{user_id}")
    def set_user_permissions(self, user_id, service_id, permissions, folder_permissions=None):
        # permissions passed in are the combined UI permissions, not DB permissions
        data = {
            "permissions": [{"permission": x} for x in translate_permissions_from_ui_to_db(permissions)],
        }

        if folder_permissions is not None:
            data["folder_permissions"] = folder_permissions

        endpoint = f"/user/{user_id}/service/{service_id}/permission"
        self.post(endpoint, data=data)

    @cache.delete("user-{user_id}")
    def set_organisation_permissions(self, user_id, organisation_id, permissions):
        self.post(f"/user/{user_id}/organisation/{organisation_id}/permissions", data={"permissions": permissions})

    def send_reset_password_url(self, email_address, next_string=None):
        endpoint = "/user/reset-password"
        data = {
            "email": email_address,
            "admin_base_url": self.admin_url,
        }
        if next_string:
            data["next"] = next_string
        self.post(endpoint, data=data)

    def find_users_by_full_or_partial_email(self, email_address):
        endpoint = "/user/find-users-by-email"
        data = {"email": email_address}
        users = self.post(endpoint, data=data)
        return users

    @cache.delete("user-{user_id}")
    def activate_user(self, user_id):
        return self.post(f"/user/{user_id}/activate", data=None)

    def send_change_email_verification(self, user_id, new_email):
        endpoint = f"/user/{user_id}/change-email-verification"
        data = {"email": new_email}
        self.post(endpoint, data)

    def get_organisations_and_services_for_user(self, user_id):
        endpoint = f"/user/{user_id}/organisations-and-services"
        return self.get(endpoint)

    def get_webauthn_credentials_for_user(self, user_id):
        endpoint = f"/user/{user_id}/webauthn"

        return self.get(endpoint)["data"]

    def create_webauthn_credential_for_user(self, user_id, credential):
        endpoint = f"/user/{user_id}/webauthn"

        return self.post(endpoint, data=credential.serialize())

    def update_webauthn_credential_name_for_user(self, *, user_id, credential_id, new_name_for_credential):
        endpoint = f"/user/{user_id}/webauthn/{credential_id}"

        return self.post(endpoint, data={"name": new_name_for_credential})

    def delete_webauthn_credential_for_user(self, *, user_id, credential_id):
        endpoint = f"/user/{user_id}/webauthn/{credential_id}"

        return self.delete(endpoint)


_user_api_client_context_var: ContextVar[UserApiClient] = ContextVar("user_api_client")
get_user_api_client: LazyLocalGetter[UserApiClient] = LazyLocalGetter(
    _user_api_client_context_var,
    lambda: UserApiClient(current_app),
)
memo_resetters.append(lambda: get_user_api_client.clear())
user_api_client = LocalProxy(get_user_api_client)

from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, _attach_current_user


class ApiKeyApiClient(NotifyAdminAPIClient):
    def get_api_keys(self, service_id):
        return self.get(url=f"/service/{service_id}/api-keys")

    def create_api_key(self, service_id, key_name, key_type):
        data = {"name": key_name, "key_type": key_type}
        data = _attach_current_user(data)
        key = self.post(url=f"/service/{service_id}/api-key", data=data)
        return key["data"]

    def revoke_api_key(self, service_id, key_id):
        data = _attach_current_user({})
        return self.post(url=f"/service/{service_id}/api-key/revoke/{key_id}", data=data)


_api_key_api_client_context_var: ContextVar[ApiKeyApiClient] = ContextVar("api_key_api_client")
get_api_key_api_client: LazyLocalGetter[ApiKeyApiClient] = LazyLocalGetter(
    _api_key_api_client_context_var,
    lambda: ApiKeyApiClient(current_app),
)
memo_resetters.append(lambda: get_api_key_api_client.clear())
api_key_api_client = LocalProxy(get_api_key_api_client)

from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, _attach_current_user


class ProviderClient(NotifyAdminAPIClient):
    def get_all_providers(self):
        return self.get(url="/provider-details")

    def get_provider_by_id(self, provider_id):
        return self.get(url=f"/provider-details/{provider_id}")

    def get_provider_versions(self, provider_id):
        return self.get(url=f"/provider-details/{provider_id}/versions")

    def update_provider(self, provider_id, priority):
        data = {"priority": priority}
        data = _attach_current_user(data)
        return self.post(url=f"/provider-details/{provider_id}", data=data)


_provider_client_context_var: ContextVar[ProviderClient] = ContextVar("provider_client")
get_provider_client: LazyLocalGetter[ProviderClient] = LazyLocalGetter(
    _provider_client_context_var,
    lambda: ProviderClient(current_app),
)
memo_resetters.append(lambda: get_provider_client.clear())
provider_client = LocalProxy(get_provider_client)

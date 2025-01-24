from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient


class ProtectedSenderIDApiClient(NotifyAdminAPIClient):
    def get_check_sender_id(self, sender_id):
        return self.get(url="/protected-sender-id/check", params={"sender_id": sender_id})


_protected_sender_id_api_client_context_var: ContextVar[ProtectedSenderIDApiClient] = ContextVar(
    "protected_sender_id_api_client"
)
get_protected_sender_id_api_client: LazyLocalGetter[ProtectedSenderIDApiClient] = LazyLocalGetter(
    _protected_sender_id_api_client_context_var,
    lambda: ProtectedSenderIDApiClient(current_app),
)
memo_resetters.append(lambda: get_protected_sender_id_api_client.clear())
protected_sender_id_api_client = LocalProxy(get_protected_sender_id_api_client)

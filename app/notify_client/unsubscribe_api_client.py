from contextvars import ContextVar

from flask import current_app
from notifications_python_client.errors import HTTPError
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient


class UnsubscribeApiClient(NotifyAdminAPIClient):

    def unsubscribe(self, notification_id, token):
        try:
            self.post(f"/unsubscribe/{notification_id}/{token}", None)
        except HTTPError as e:
            if e.status_code == 404:
                return False
            raise e
        return True


_unsubscribe_api_client_context_var: ContextVar[UnsubscribeApiClient] = ContextVar("unsubscribe_api_client")
get_unsubscribe_api_client: LazyLocalGetter[UnsubscribeApiClient] = LazyLocalGetter(
    _unsubscribe_api_client_context_var,
    lambda: UnsubscribeApiClient(current_app),
)
memo_resetters.append(lambda: get_unsubscribe_api_client.clear())
unsubscribe_api_client = LocalProxy(get_unsubscribe_api_client)

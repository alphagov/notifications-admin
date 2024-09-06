from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient


class EventsApiClient(NotifyAdminAPIClient):
    def create_event(self, event_type, event_data):
        data = {"event_type": event_type, "data": event_data}
        resp = self.post(url="/events", data=data)
        return resp["data"]


_events_api_client_context_var: ContextVar[EventsApiClient] = ContextVar("events_api_client")
get_events_api_client: LazyLocalGetter[EventsApiClient] = LazyLocalGetter(
    _events_api_client_context_var,
    lambda: EventsApiClient(current_app),
)
memo_resetters.append(lambda: get_events_api_client.clear())
events_api_client = LocalProxy(get_events_api_client)

from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, cache


class InboundNumberClient(NotifyAdminAPIClient):
    def get_available_inbound_sms_numbers(self):
        return self.get(url="/inbound-number/available")

    def get_all_inbound_sms_number_service(self):
        return self.get("/inbound-number")

    def get_inbound_sms_number_for_service(self, service_id):
        return self.get(f"/inbound-number/service/{service_id}")

    @cache.delete("service-{service_id}")
    @cache.delete_by_pattern("service-{service_id}-template-*")
    def add_inbound_number_to_service(self, service_id, inbound_number_id=None):
        data = {}

        if inbound_number_id:
            data["inbound_number_id"] = inbound_number_id

        return self.post(f"inbound-number/service/{service_id}", data=data)


_inbound_number_client_context_var: ContextVar[InboundNumberClient] = ContextVar("inbound_number_client")
get_inbound_number_client: LazyLocalGetter[InboundNumberClient] = LazyLocalGetter(
    _inbound_number_client_context_var,
    lambda: InboundNumberClient(current_app),
)
memo_resetters.append(lambda: get_inbound_number_client.clear())
inbound_number_client = LocalProxy(get_inbound_number_client)

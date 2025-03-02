from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, api_client_request_session, cache


class SMSRateApiClient(NotifyAdminAPIClient):
    @cache.set("sms-rate", ttl_in_seconds=3_600)
    def get_sms_rate(self):
        return self.get(url="/sms-rate")


_sms_rate_api_client_context_var: ContextVar[SMSRateApiClient] = ContextVar("sms_rate_api_client")
get_sms_rate_api_client: LazyLocalGetter[SMSRateApiClient] = LazyLocalGetter(
    _sms_rate_api_client_context_var,
    lambda: SMSRateApiClient(current_app, request_session=api_client_request_session),
)
memo_resetters.append(lambda: get_sms_rate_api_client.clear())
sms_rate_api_client = LocalProxy(get_sms_rate_api_client)

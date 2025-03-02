from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, api_client_request_session, cache


class LetterRateApiClient(NotifyAdminAPIClient):
    @cache.set("letter-rates", ttl_in_seconds=3_600)
    def get_letter_rates(self):
        return self.get(url="/letter-rates")


_letter_rate_api_client_context_var: ContextVar[LetterRateApiClient] = ContextVar("letter_rate_api_client")
get_letter_rate_api_client: LazyLocalGetter[LetterRateApiClient] = LazyLocalGetter(
    _letter_rate_api_client_context_var,
    lambda: LetterRateApiClient(current_app, request_session=api_client_request_session),
)
memo_resetters.append(lambda: get_letter_rate_api_client.clear())
letter_rate_api_client = LocalProxy(get_letter_rate_api_client)

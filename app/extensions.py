from contextvars import ContextVar

from flask import current_app
from notifications_utils.clients.antivirus.antivirus_client import AntivirusClient
from notifications_utils.clients.redis.redis_client import RedisClient
from notifications_utils.clients.zendesk.zendesk_client import ZendeskClient
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters

_antivirus_client_context_var: ContextVar[AntivirusClient] = ContextVar("antivirus_client")
get_antivirus_client: LazyLocalGetter[AntivirusClient] = LazyLocalGetter(
    _antivirus_client_context_var,
    lambda: AntivirusClient(
        api_host=current_app.config["ANTIVIRUS_API_HOST"],
        auth_token=current_app.config["ANTIVIRUS_API_KEY"],
    ),
)
memo_resetters.append(lambda: get_antivirus_client.clear())
antivirus_client = LocalProxy(get_antivirus_client)

_zendesk_client_context_var: ContextVar[ZendeskClient] = ContextVar("zendesk_client")
get_zendesk_client: LazyLocalGetter[ZendeskClient] = LazyLocalGetter(
    _zendesk_client_context_var,
    lambda: ZendeskClient(
        api_key=current_app.config["ZENDESK_API_KEY"],
    ),
)
memo_resetters.append(lambda: get_zendesk_client.clear())
zendesk_client = LocalProxy(get_zendesk_client)

redis_client = RedisClient()

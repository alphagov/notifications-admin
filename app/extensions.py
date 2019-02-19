from notifications_utils.clients.antivirus.antivirus_client import (
    AntivirusClient,
)
from notifications_utils.clients.redis.redis_client import RedisClient
from notifications_utils.clients.statsd.statsd_client import StatsdClient
from notifications_utils.clients.zendesk.zendesk_client import ZendeskClient

antivirus_client = AntivirusClient()
statsd_client = StatsdClient()
zendesk_client = ZendeskClient()
redis_client = RedisClient()

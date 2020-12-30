from notifications_utils.clients.antivirus.antivirus_client import (
    AntivirusClient,
)
from notifications_utils.clients.redis.redis_client import RedisClient
from notifications_utils.clients.zendesk.zendesk_client import ZendeskClient
from server_timing import Timing


class TimingRedisClient(RedisClient):

    def init_app(self, app):
        self.server_timing = Timing(app)
        super().init_app(app)

    def get(self, key, raise_exception=False):
        with self.server_timing.time(f'Redis--{key}'):
            return super().get(key, raise_exception=raise_exception)


antivirus_client = AntivirusClient()
zendesk_client = ZendeskClient()
redis_client = TimingRedisClient()

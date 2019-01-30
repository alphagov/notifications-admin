
from app.notify_client import NotifyAdminAPIClient


class StatusApiClient(NotifyAdminAPIClient):

    def get_status(self, *params):
        return self.get(url='/_status', *params)


status_api_client = StatusApiClient()

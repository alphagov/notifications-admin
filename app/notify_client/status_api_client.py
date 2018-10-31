
from app.notify_client import NotifyAdminAPIClient


class StatusApiClient(NotifyAdminAPIClient):
    def __init__(self):
        super().__init__("a" * 73, "b")

    def get_status(self, *params):
        return self.get(url='/_status', *params)


status_api_client = StatusApiClient()

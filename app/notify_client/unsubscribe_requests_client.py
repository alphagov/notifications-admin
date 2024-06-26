from app.notify_client import NotifyAdminAPIClient


class UnsubscribeRequestsApiClient(NotifyAdminAPIClient):
    def get_pending_unsubscribe_requests(self, service_id):
        return 300  # stub for now, before building the backend


unsubscribe_requests_client = UnsubscribeRequestsApiClient()

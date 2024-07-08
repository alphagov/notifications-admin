from app.notify_client import NotifyAdminAPIClient


class UnsubscribeRequestsApiClient(NotifyAdminAPIClient):
    def get_pending_unsubscribe_requests(self, service_id):
        return {
            "count_of_pending_unsubscribe_requests": 300,
            "datetime_of_latest_unsubscribe_request": "2024-07-01T12:12:12.1234",
        }


unsubscribe_requests_client = UnsubscribeRequestsApiClient()

from app.notify_client import NotifyAdminAPIClient


class EventsApiClient(NotifyAdminAPIClient):
    def create_event(self, event_type, event_data):
        data = {"event_type": event_type, "data": event_data}
        resp = self.post(url="/events", data=data)
        return resp["data"]


events_api_client = EventsApiClient()

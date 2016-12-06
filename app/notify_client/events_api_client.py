from app.notify_client import NotifyAdminAPIClient


class EventsApiClient(NotifyAdminAPIClient):
    def __init__(self):
        super().__init__("a", "b", "c")

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.service_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.api_key = app.config['ADMIN_CLIENT_SECRET']

    def create_event(self, event_type, event_data):
        data = {
            'event_type': event_type,
            'data': event_data
        }
        resp = self.post(url='/events', data=data)
        return resp['data']

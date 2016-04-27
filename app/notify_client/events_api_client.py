from notifications_python_client.base import BaseAPIClient


class EventsApiClient(BaseAPIClient):
    def __init__(self, base_url=None, client_id=None, secret=None):
        super(self.__class__, self).__init__(base_url=base_url or 'base_url',
                                             client_id=client_id or 'client_id',
                                             secret=secret or 'secret')

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.client_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.secret = app.config['ADMIN_CLIENT_SECRET']

    def create_event(self, event_type, event_data):
        data = {
            'event_type': event_type,
            'data': event_data
        }
        resp = self.post(url='/events', data=data)
        return resp['data']

from app.notify_client import NotifyAdminAPIClient


class InboundNumberClient(NotifyAdminAPIClient):

    def __init__(self):
        super().__init__("a" * 73, "b")

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.service_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.api_key = app.config['ADMIN_CLIENT_SECRET']

    def get_available_inbound_sms_numbers(self):
        return self.get(url='/inbound-number/available')

    def get_all_inbound_sms_number_service(self):
        return self.get('/inbound-number')

    def get_inbound_sms_number_for_service(self, service_id):
        return self.get('/inbound-number/service/{}'.format(service_id))

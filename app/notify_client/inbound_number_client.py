from app.notify_client import NotifyAdminAPIClient

class InboundNumberClient(NotifyAdminAPIClient):

    def __init__(self):
        super().__init__("a" * 73, "b")

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.service_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.api_key = app.config['ADMIN_CLIENT_SECRET']

    def get_all_inbound_sms_number_service(self):

        return self.get('/inbound_number')

    def get_inbound_sms_number_for_service(self, service_id):
        return self.get('/inbound_number/service/{}'.format(service_id))

    # def activate_inbound_sms_service(self, service_id, inbound_number_id):
    #     return self.post(url='/inbound_number/{}/service/{}'.format(inbound_number_id, service_id), data={})

    def reactivate_inbound_sms_service(self, inbound_number_id):
        try:


        catch:

        return self.post(url='/inbound_number/{}/on'.format(inbound_number_id), data={})

    def deactivate_inbound_sms_permission(self, inbound_number_id):
        return self.post(url='/inbound_number/{}/off'.format(inbound_number_id), data={})

    # def get_available_inbound_number(self):
    #     return self.get(url='/inbound_number/available'.format())

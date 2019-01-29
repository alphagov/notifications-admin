from app.notify_client import NotifyAdminAPIClient


class InboundNumberClient(NotifyAdminAPIClient):

    def get_available_inbound_sms_numbers(self):
        return self.get(url='/inbound-number/available')

    def get_all_inbound_sms_number_service(self):
        return self.get('/inbound-number')

    def get_inbound_sms_number_for_service(self, service_id):
        return self.get('/inbound-number/service/{}'.format(service_id))


inbound_number_client = InboundNumberClient()

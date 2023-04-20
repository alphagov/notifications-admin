from app.notify_client import NotifyAdminAPIClient, cache


class InboundNumberClient(NotifyAdminAPIClient):
    def get_available_inbound_sms_numbers(self):
        return self.get(url="/inbound-number/available")

    def get_all_inbound_sms_number_service(self):
        return self.get("/inbound-number")

    def get_inbound_sms_number_for_service(self, service_id):
        return self.get(f"/inbound-number/service/{service_id}")

    @cache.delete("service-{service_id}")
    @cache.delete_by_pattern("service-{service_id}-template-*")
    def add_inbound_number_to_service(self, service_id, inbound_number_id=None):
        data = {}

        if inbound_number_id:
            data["inbound_number_id"] = inbound_number_id

        return self.post(f"inbound-number/service/{service_id}", data=data)


inbound_number_client = InboundNumberClient()

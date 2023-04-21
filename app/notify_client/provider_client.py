from app.notify_client import NotifyAdminAPIClient, _attach_current_user


class ProviderClient(NotifyAdminAPIClient):
    def get_all_providers(self):
        return self.get(url="/provider-details")

    def get_provider_by_id(self, provider_id):
        return self.get(url=f"/provider-details/{provider_id}")

    def get_provider_versions(self, provider_id):
        return self.get(url=f"/provider-details/{provider_id}/versions")

    def update_provider(self, provider_id, priority):
        data = {"priority": priority}
        data = _attach_current_user(data)
        return self.post(url=f"/provider-details/{provider_id}", data=data)


provider_client = ProviderClient()

from app.notify_client import NotifyAdminAPIClient, cache


class StatusApiClient(NotifyAdminAPIClient):

    def get_status(self, *params):
        return self.get(url='/_status', *params)

    @cache.set('live-service-and-organisation-counts', ttl_in_seconds=3600)
    def get_count_of_live_services_and_organisations(self):
        return self.get(url='/_status/live-service-and-organisation-counts')


status_api_client = StatusApiClient()

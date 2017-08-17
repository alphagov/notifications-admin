from app.notify_client import NotifyAdminAPIClient


class BillingAPIClient(NotifyAdminAPIClient):
    # Fudge assert in the super __init__ so
    # we can set those variables later.
    def __init__(self):
        super().__init__("a" * 73, "b")

    def init_app(self, application):
        self.base_url = application.config['API_HOST_NAME']
        self.service_id = application.config['ADMIN_CLIENT_USER_NAME']
        self.api_key = application.config['ADMIN_CLIENT_SECRET']

    def get_billable_units(self, service_id, year):
        return self.get(
            '/service/{0}/billing/monthly-usage'.format(service_id),
            params=dict(year=year)
        )

    def get_service_usage(self, service_id, year=None):
        return self.get(
            '/service/{0}/billing/yearly-usage'.format(service_id),
            params=dict(year=year)
        )

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
            '/service/{0}/billing/yearly-usage-summary'.format(service_id),
            params=dict(year=year)
        )

    def get_free_sms_fragment_limit_for_year(self, service_id, year=None):
        result = self.get(
            '/service/{0}/billing/free-sms-fragment-limit'.format(service_id),
            params=dict(financial_year_start=year)
        )
        return result['free_sms_fragment_limit']

    def get_free_sms_fragment_limit_for_all_years(self, service_id, year=None):
        return self.get(
            '/service/{0}/billing/free-sms-fragment-limit'.format(service_id))

    def create_or_update_free_sms_fragment_limit(self, service_id, free_sms_fragment_limit, year=None):
        # year = None will update current and future year in the API
        data = {
            "financial_year_start": year,
            "free_sms_fragment_limit": free_sms_fragment_limit
        }

        return self.post(
            url='/service/{0}/billing/free-sms-fragment-limit'.format(service_id),
            data=data
        )

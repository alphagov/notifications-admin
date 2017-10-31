from app.notify_client import NotifyAdminAPIClient
from flask import current_app
from notifications_python_client.errors import HTTPError


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
        try:
            if year is None:
                result = self.get(
                    '/service/{0}/billing/free-sms-fragment-limit/current-year'.format(service_id)
                )
            else:
                result = self.get(
                    '/service/{0}/billing/free-sms-fragment-limit'.format(service_id),
                    params=dict(financial_year_start=year)
                )
            return result['free_sms_fragment_limit']
        except HTTPError:
            current_app.logger.info(
                'Requested free_sms_fragment_limit entry for service {0} and year {1} does not exist'
                .format(service_id, year))
            return -1

    def get_free_sms_fragment_limit_for_all_years(self, service_id, year=None):
        try:
            return self.get(
                '/service/{0}/billing/free-sms-fragment-limit'.format(service_id),
            )
        except HTTPError:
            current_app.logger.info(
                'No free_sms_fragment_limit entry exists for service {0} '
                .format(service_id, year))
            return []

    def create_or_update_free_sms_fragment_limit_for_year(self, service_id, free_sms_fragment_limit, year=None):
        if year is None:
            data = {
                "free_sms_fragment_limit": free_sms_fragment_limit,
            }
        else:
            data = {
                "financial_year_start": year,
                "free_sms_fragment_limit": free_sms_fragment_limit,
            }
        return self.post(
            url='/service/{0}/billing/free-sms-fragment-limit'.format(service_id),
            data=data
        )

from app.notify_client import NotifyAdminAPIClient


class BillingAPIClient(NotifyAdminAPIClient):

    def get_monthly_usage_for_service(self, service_id, year):
        return self.get(
            '/service/{0}/billing/monthly-usage'.format(service_id),
            params=dict(year=year)
        )

    def get_annual_usage_for_service(self, service_id, year=None):
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

    def get_data_for_billing_report(self, start_date, end_date):
        return self.get(url='/platform-stats/data-for-billing-report',
                        params={
                            'start_date': str(start_date),
                            'end_date': str(end_date),
                        })

    def get_data_for_volumes_by_service_report(self, start_date, end_date):
        return self.get(url='/platform-stats/volumes-by-service',
                        params={
                            'start_date': str(start_date),
                            'end_date': str(end_date),
                        })

    def get_data_for_daily_volumes_report(self, start_date, end_date):
        return self.get(url='/platform-stats/daily-volumes-report',
                        params={
                            'start_date': str(start_date),
                            'end_date': str(end_date),
                        })

    def get_data_for_daily_sms_provider_volumes_report(self, start_date, end_date):
        return self.get(
            url='/platform-stats/daily-sms-provider-volumes-report',
            params={
                'start_date': str(start_date),
                'end_date': str(end_date),
            }
        )


billing_api_client = BillingAPIClient()

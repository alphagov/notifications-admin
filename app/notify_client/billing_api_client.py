from app.notify_client import NotifyAdminAPIClient


class BillingAPIClient(NotifyAdminAPIClient):
    def get_monthly_usage_for_service(self, service_id, year):
        return self.get(f"/service/{service_id}/billing/monthly-usage", params=dict(year=year))

    def get_annual_usage_for_service(self, service_id, year=None):
        return self.get(f"/service/{service_id}/billing/yearly-usage-summary", params=dict(year=year))

    def get_free_sms_fragment_limit_for_year(self, service_id, year=None):
        result = self.get(
            f"/service/{service_id}/billing/free-sms-fragment-limit", params=dict(financial_year_start=year)
        )
        return result["free_sms_fragment_limit"]

    def create_or_update_free_sms_fragment_limit(self, service_id, free_sms_fragment_limit, year=None):
        # year = None will update current and future year in the API
        data = {"financial_year_start": year, "free_sms_fragment_limit": free_sms_fragment_limit}

        return self.post(url=f"/service/{service_id}/billing/free-sms-fragment-limit", data=data)

    def get_data_for_billing_report(self, start_date, end_date):
        return self.get(
            url="/platform-stats/data-for-billing-report",
            params={
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )

    def get_data_for_volumes_by_service_report(self, start_date, end_date):
        return self.get(
            url="/platform-stats/volumes-by-service",
            params={
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )

    def get_data_for_daily_volumes_report(self, start_date, end_date):
        return self.get(
            url="/platform-stats/daily-volumes-report",
            params={
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )

    def get_data_for_daily_sms_provider_volumes_report(self, start_date, end_date):
        return self.get(
            url="/platform-stats/daily-sms-provider-volumes-report",
            params={
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )


billing_api_client = BillingAPIClient()

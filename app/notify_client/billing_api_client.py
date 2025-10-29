from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, api_client_request_session


class BillingAPIClient(NotifyAdminAPIClient):
    def get_monthly_usage_for_service(self, service_id, year):
        return self.get(f"/service/{service_id}/billing/monthly-usage", params={"year": year})

    def get_annual_usage_for_service(self, service_id, year=None):
        return self.get(f"/service/{service_id}/billing/yearly-usage-summary", params={"year": year})

    def get_free_sms_fragment_limit_for_year(self, service_id, year=None):
        result = self.get(
            f"/service/{service_id}/billing/free-sms-fragment-limit", params={"financial_year_start": year}
        )
        return result["free_sms_fragment_limit"]

    def create_or_update_free_sms_fragment_limit(self, service_id, free_sms_fragment_limit):
        """
        Updates the free sms fragment limit for the current financial year
        """
        data = {"free_sms_fragment_limit": free_sms_fragment_limit}

        return self.post(url=f"/service/{service_id}/billing/free-sms-fragment-limit", data=data)

    def get_data_for_billing_report(self, start_date, end_date):
        return self.get(
            url="/platform-stats/data-for-billing-report",
            params={
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )

    def get_data_for_dvla_billing_report(self, start_date, end_date):
        return self.get(
            url="/platform-stats/data-for-dvla-billing-report",
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


_billing_api_client_context_var: ContextVar[BillingAPIClient] = ContextVar("billing_api_client")
get_billing_api_client: LazyLocalGetter[BillingAPIClient] = LazyLocalGetter(
    _billing_api_client_context_var,
    lambda: BillingAPIClient(current_app, request_session=api_client_request_session),
)
memo_resetters.append(lambda: get_billing_api_client.clear())
billing_api_client = LocalProxy(get_billing_api_client)

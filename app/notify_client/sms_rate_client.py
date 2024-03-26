from app.notify_client import NotifyAdminAPIClient, cache


class SMSRateApiClient(NotifyAdminAPIClient):
    @cache.set("sms-rate", ttl_in_seconds=3_600)
    def get_sms_rate(self):
        return self.get(url="/sms-rate")


sms_rate_api_client = SMSRateApiClient()

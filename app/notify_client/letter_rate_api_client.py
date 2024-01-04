from app.notify_client import NotifyAdminAPIClient, cache


class LetterRateApiClient(NotifyAdminAPIClient):
    @cache.set("letter-rates", ttl_in_seconds=3_600)
    def get_letter_rates(self):
        return self.get(url="/letter-rates")


letter_rate_api_client = LetterRateApiClient()

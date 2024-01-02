from app.notify_client import NotifyAdminAPIClient, cache


class LetterRateApiClient(NotifyAdminAPIClient):
    @cache.set("letter-rates")
    def get_letter_rates(self):
        return self.get(url="/letter-rates")


letter_rate_api_client = LetterRateApiClient()

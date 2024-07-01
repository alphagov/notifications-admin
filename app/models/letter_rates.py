from app.models import JSONModel, ModelList
from app.notify_client.letter_rate_api_client import letter_rate_api_client


class LetterRate(JSONModel):
    ALLOWED_PROPERTIES = {"sheet_count", "rate", "post_class", "start_date"}
    __sort_attribute__ = "rate"

    @property
    def rate_in_pennies(self):
        return int(round(float(self.rate) * 100))


class LetterRates(ModelList):
    model = LetterRate
    client_method = letter_rate_api_client.get_letter_rates

    post_classes = {
        # The API doesn’t store names or a sort order for the classes
        # so we define them here.
        "second": "Second class",
        "first": "First class",
        # The API will return rows for `europe` and `rest-of-world`.
        # At the moment the rates for both are the same. So we treat
        # `europe` as meaning `international` and ignore the values
        # for `rest-of-world`
        "europe": "International",
    }

    @property
    def rates(self):
        return tuple(rate.rate_in_pennies for rate in self)

    @property
    def sheet_counts(self):
        return sorted({rate.sheet_count for rate in self})

    @property
    def last_updated(self):
        return max(rate.start_date for rate in self)

    def get(self, *, sheet_count, post_class):
        for rate in self:
            if rate.sheet_count == sheet_count and rate.post_class == post_class:
                return rate.rate_in_pennies
        raise KeyError

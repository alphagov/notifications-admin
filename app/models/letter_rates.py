from datetime import datetime
from typing import Any

from app.models import JSONModel, ModelList
from app.notify_client.letter_rate_api_client import letter_rate_api_client


class LetterRate(JSONModel):
    sheet_count: int
    rate: float
    post_class: Any
    start_date: datetime

    __sort_attribute__ = "rate"

    @property
    def rate_in_pennies(self):
        return int(round(self.rate * 100))


class LetterRates(ModelList):
    model = LetterRate

    post_classes = {
        # The API doesn’t store names or a sort order for the classes
        # so we define them here.
        "economy": "Economy mail",
        "second": "Second class",
        "first": "First class",
        # The API will return rows for `europe` and `rest-of-world`.
        # At the moment the rates for both are the same. So we treat
        # `europe` as meaning `international` and ignore the values
        # for `rest-of-world`
        "europe": "International",
    }

    @staticmethod
    def _get_items(*args, **kwargs):
        return letter_rate_api_client.get_letter_rates(*args, **kwargs)

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

from app.formatters import format_pennies_as_currency
from app.models import JSONModel
from app.notify_client.sms_rate_client import sms_rate_api_client


class SMSRate(JSONModel):
    ALLOWED_PROPERTIES = {
        "rate",
        "valid_from",
    }
    __sort_attribute__ = "valid_from"

    def __init__(self):
        super().__init__(sms_rate_api_client.get_sms_rate())

    def __str__(self):
        return format_pennies_as_currency(self.rate_in_pennies, long=True)

    def __eq__(self, other):
        return self.rate_in_pennies == float(other)

    @property
    def rate_in_pennies(self):
        return float(self.rate * 100)

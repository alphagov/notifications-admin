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
        return str(self.rate)

    def __eq__(self, other):
        return float(self.rate) == float(other)

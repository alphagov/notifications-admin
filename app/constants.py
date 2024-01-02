# Organisation user permission codes
import enum

PERMISSION_CAN_MAKE_SERVICES_LIVE = "can_make_services_live"

# Error codes from the API
QR_CODE_TOO_LONG = "qr-code-too-long"


# Language options supported for bilingual letter templates
class LetterLanguageOptions(str, enum.Enum):
    english = "english"
    welsh_then_english = "welsh_then_english"


LETTER_PRICES_BY_SHEETS = {
    1: {"second": 54, "first": 82, "international": 144},
    2: {"second": 59, "first": 86, "international": 149},
    3: {"second": 63, "first": 90, "international": 153},
    4: {"second": 68, "first": 96, "international": 158},
    5: {"second": 73, "first": 100, "international": 163},
}
MIN_LETTER_PRICE = min(pennies for prices in LETTER_PRICES_BY_SHEETS.values() for pennies in prices.values())
MAX_LETTER_PRICE = max(pennies for prices in LETTER_PRICES_BY_SHEETS.values() for pennies in prices.values())

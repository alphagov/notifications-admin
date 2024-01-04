# Organisation user permission codes
import enum

PERMISSION_CAN_MAKE_SERVICES_LIVE = "can_make_services_live"

# Error codes from the API
QR_CODE_TOO_LONG = "qr-code-too-long"


# Language options supported for bilingual letter templates
class LetterLanguageOptions(str, enum.Enum):
    english = "english"
    welsh_then_english = "welsh_then_english"

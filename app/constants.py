# Organisation user permission codes
import enum

JSON_UPDATES_BLUEPRINT_NAME = "json_updates"
NO_COOKIE_BLUEPRINT_NAME = "no_cookie"

MAX_NOTIFICATION_FOR_DOWNLOAD = 250000

PERMISSION_CAN_MAKE_SERVICES_LIVE = "can_make_services_live"

# Sign in methods
SIGN_IN_METHOD_TEXT = "text"
SIGN_IN_METHOD_TEXT_OR_EMAIL = "text-or-email"

# Service Join Request statuses
SERVICE_JOIN_REQUEST_PENDING = "pending"
SERVICE_JOIN_REQUEST_APPROVED = "approved"
SERVICE_JOIN_REQUEST_REJECTED = "rejected"
SERVICE_JOIN_REQUEST_CANCELLED = "cancelled"

# Report request report statuses
REPORT_REQUEST_PENDING = "pending"
REPORT_REQUEST_IN_PROGRESS = "in progress"
REPORT_REQUEST_STORED = "stored"
REPORT_REQUEST_FAILED = "failed"
REPORT_REQUEST_DELETED = "deleted"

# Error codes from the API
QR_CODE_TOO_LONG = "qr-code-too-long"

# Allow upto 800,000 notifications to be requested in a report for phase 1a
REPORT_REQUEST_MAX_NOTIFICATIONS = 800_000


# Language options supported for bilingual letter templates
class LetterLanguageOptions(str, enum.Enum):
    english = "english"
    welsh_then_english = "welsh_then_english"


# Service callbacks
class ServiceCallbackTypes(enum.StrEnum):
    delivery_status = "delivery_status"
    complaint = "complaint"
    returned_letter = "returned_letter"
    inbound_sms = "inbound_sms"

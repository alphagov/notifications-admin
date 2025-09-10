import json
import os


class Config:
    ADMIN_CLIENT_SECRET = os.environ.get("ADMIN_CLIENT_SECRET")
    API_HOST_NAME = os.environ.get("API_HOST_NAME")
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DANGEROUS_SALT = os.environ.get("DANGEROUS_SALT")
    ZENDESK_API_KEY = os.environ.get("ZENDESK_API_KEY")

    # if we're not on cloudfoundry, we can get to this app from localhost. but on cloudfoundry its different
    ADMIN_BASE_URL = os.environ.get("ADMIN_BASE_URL", "http://localhost:6012")

    TEMPLATE_PREVIEW_API_HOST = os.environ.get("TEMPLATE_PREVIEW_API_HOST", "http://localhost:6013")
    TEMPLATE_PREVIEW_API_KEY = os.environ.get("TEMPLATE_PREVIEW_API_KEY", "my-secret-key")

    # Logging
    DEBUG = False
    NOTIFY_REQUEST_LOG_LEVEL = os.getenv("NOTIFY_REQUEST_LOG_LEVEL", "INFO")

    ADMIN_CLIENT_USER_NAME = "notify-admin"

    ANTIVIRUS_API_HOST = os.environ.get("ANTIVIRUS_API_HOST")
    ANTIVIRUS_API_KEY = os.environ.get("ANTIVIRUS_API_KEY")

    ASSETS_DEBUG = False
    AWS_REGION = "eu-west-1"
    DEFAULT_SERVICE_LIMIT = 50
    DEFAULT_SERVICE_INTERNATIONAL_SMS_LIMIT = 100
    DEFAULT_LIVE_SERVICE_RATE_LIMITS = {
        "email": 250_000,
        "sms": 250_000,
        "letter": 20_000,
    }

    EMAIL_EXPIRY_SECONDS = 3600  # 1 hour
    INVITATION_EXPIRY_SECONDS = 3600 * 24 * 2  # 2 days - also set on api
    EMAIL_2FA_EXPIRY_SECONDS = 1800  # 30 Minutes

    # mix(govuk-colour("dark-grey"), govuk-colour("mid-grey"))
    HEADER_COLOUR = os.environ.get("HEADER_COLOUR", "#81878b")
    HTTP_PROTOCOL = os.environ.get("HTTP_PROTOCOL", "http")
    NOTIFY_APP_NAME = "admin"
    NOTIFY_LOG_LEVEL = "DEBUG"

    # Session config
    PERMANENT_SESSION_LIFETIME = 20 * 60 * 60  # 20 hours in seconds
    PLATFORM_ADMIN_INACTIVE_SESSION_TIMEOUT = 30 * 60  # 30 minutes in seconds
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_NAME = "notify_admin_session"
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # don't send back the cookie if it hasn't been modified by the request. this means that the expiry time won't be
    # updated unless the session is changed - but it's generally refreshed by `save_service_or_org_after_request`
    # every time anyway, except for specific endpoints (png/pdfs generally) where we've disabled that handler.
    SESSION_REFRESH_EACH_REQUEST = False

    SEND_FILE_MAX_AGE_DEFAULT = 365 * 24 * 60 * 60  # 1 year
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    ACTIVITY_STATS_LIMIT_DAYS = 7

    REPLY_TO_EMAIL_ADDRESS_VALIDATION_TIMEOUT = int(os.environ.get("REPLY_TO_EMAIL_ADDRESS_VALIDATION_TIMEOUT", 45))

    NOTIFY_ENVIRONMENT = os.environ.get("NOTIFY_ENVIRONMENT", "development")
    S3_BUCKET_CSV_UPLOAD = os.environ.get("S3_BUCKET_CSV_UPLOAD", "local-notifications-csv-upload")
    S3_BUCKET_CONTACT_LIST_UPLOAD = os.environ.get("S3_BUCKET_CONTACT_LIST_UPLOAD", "local-contact-list")
    S3_BUCKET_LOGO_UPLOAD = os.environ.get("S3_BUCKET_LOGO_UPLOAD", "public-logos-local")
    S3_BUCKET_MOU = os.environ.get("S3_BUCKET_MOU", "local-mou")
    S3_BUCKET_TRANSIENT_UPLOADED_LETTERS = os.environ.get(
        "S3_BUCKET_TRANSIENT_UPLOADED_LETTERS", "local-transient-uploaded-letters"
    )
    S3_BUCKET_PRECOMPILED_ORIGINALS_BACKUP_LETTERS = os.environ.get(
        "S3_BUCKET_PRECOMPILED_ORIGINALS_BACKUP_LETTERS", "local-precompiled-originals-backup-letters"
    )
    S3_BUCKET_LETTER_ATTACHMENTS = os.environ.get("S3_BUCKET_LETTER_ATTACHMENTS", "local-letter-attachments")
    S3_BUCKET_REPORT_REQUESTS_DOWNLOAD = os.environ.get(
        "S3_BUCKET_REPORT_REQUESTS_DOWNLOAD", "local-report-requests-download"
    )
    LOGO_CDN_DOMAIN = os.environ.get("LOGO_CDN_DOMAIN", "static-logos.notify.tools")
    ANTIVIRUS_ENABLED = True

    REDIS_URL = os.environ.get("REDIS_URL")
    REDIS_ENABLED = False if os.environ.get("REDIS_ENABLED") == "0" else True

    ASSET_DOMAIN = os.environ.get("ASSET_DOMAIN", "")
    ASSET_PATH = os.environ.get("ASSET_PATH", "/static/")

    NOTIFY_SERVICE_ID = "d6aa2c68-a2d9-4437-ab19-3ae8eb202553"

    BILLING_DETAILS = json.loads(os.environ.get("BILLING_DETAILS") or "null") or {
        "account_number": "98765432",
        "sort_code": "01-23-45",
        "IBAN": "GB33BUKB20201555555555",
        "swift": "ABCDEF12",
        "notify_billing_email_address": "generic@digital.cabinet-office.gov.uk",
    }

    EMAIL_BRANDING_MIN_LOGO_HEIGHT_PX = 108
    EMAIL_BRANDING_MAX_LOGO_WIDTH_PX = 640

    FEEDBACK_ZENDESK_SUBJECT_PREFIX_ENABLED = os.environ.get("FEEDBACK_ZENDESK_SUBJECT_PREFIX_ENABLED", "1") == "1"


class Development(Config):
    SERVER_NAME = os.getenv("SERVER_NAME")
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SESSION_PROTECTION = None
    S3_BUCKET_CSV_UPLOAD = "development-notifications-csv-upload"
    S3_BUCKET_CONTACT_LIST_UPLOAD = "development-contact-list"
    S3_BUCKET_LOGO_UPLOAD = "public-logos-tools"
    S3_BUCKET_MOU = "notify.tools-mou"
    S3_BUCKET_TRANSIENT_UPLOADED_LETTERS = "development-transient-uploaded-letters"
    S3_BUCKET_PRECOMPILED_ORIGINALS_BACKUP_LETTERS = "development-letters-precompiled-originals-backup"
    S3_BUCKET_LETTER_ATTACHMENTS = "development-letter-attachments"
    S3_BUCKET_REPORT_REQUESTS_DOWNLOAD = "development-report-requests-download"

    LOGO_CDN_DOMAIN = "static-logos.notify.tools"

    ADMIN_CLIENT_SECRET = "dev-notify-secret-key"
    DANGEROUS_SALT = "dev-notify-salt"
    SECRET_KEY = "dev-notify-secret-key"
    API_HOST_NAME = os.environ.get("API_HOST_NAME", "http://localhost:6011")
    ANTIVIRUS_API_HOST = os.environ.get("ANTIVIRUS_API_HOST", "http://localhost:6016")
    ANTIVIRUS_API_KEY = "test-key"
    ANTIVIRUS_ENABLED = os.getenv("ANTIVIRUS_ENABLED") == "1"

    ASSET_PATH = "/static/"

    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    REDIS_ENABLED = os.environ.get("REDIS_ENABLED") == "1"


class Test(Development):
    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False
    S3_BUCKET_CSV_UPLOAD = "test-notifications-csv-upload"
    S3_BUCKET_CONTACT_LIST_UPLOAD = "test-contact-list"
    S3_BUCKET_LOGO_UPLOAD = "public-logos-test"
    S3_BUCKET_MOU = "test-mou"
    S3_BUCKET_TRANSIENT_UPLOADED_LETTERS = "test-transient-uploaded-letters"
    S3_BUCKET_PRECOMPILED_ORIGINALS_BACKUP_LETTERS = "test-letters-precompiled-originals-backup"
    S3_BUCKET_LETTER_ATTACHMENTS = "test-letter-attachments"
    S3_BUCKET_REPORT_REQUESTS_DOWNLOAD = "test-report-requests-download"
    LOGO_CDN_DOMAIN = "static-logos.test.com"
    NOTIFY_ENVIRONMENT = "test"
    API_HOST_NAME = "http://you-forgot-to-mock-an-api-call-to"
    TEMPLATE_PREVIEW_API_HOST = "http://localhost:9999"
    ANTIVIRUS_API_HOST = "https://test-antivirus"
    ANTIVIRUS_API_KEY = "test-antivirus-secret"
    ANTIVIRUS_ENABLED = True

    ASSET_DOMAIN = "static.example.com"
    ASSET_PATH = "https://static.example.com/"


class CloudFoundryConfig(Config):
    pass


# CloudFoundry sandbox
class Sandbox(CloudFoundryConfig):
    HTTP_PROTOCOL = "https"
    HEADER_COLOUR = "#F499BE"  # $baby-pink
    S3_BUCKET_CSV_UPLOAD = "cf-sandbox-notifications-csv-upload"
    S3_BUCKET_LOGO_UPLOAD = "cf-sandbox-notifications-logo-upload"
    NOTIFY_ENVIRONMENT = "sandbox"


##########################
### NotifyNL overrides ###
##########################
NL_PREFIX = "notifynl"


class DevNL(Config):
    NOTIFY_ENVIRONMENT = "development"

    SERVER_NAME = os.getenv("SERVER_NAME")
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SESSION_PROTECTION = None

    S3_BUCKET_CSV_UPLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-notifications-csv-upload"
    S3_BUCKET_CONTACT_LIST_UPLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-contact-list"
    S3_BUCKET_LOGO_UPLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-public-logos-tools"
    S3_BUCKET_MOU = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-mou"
    S3_BUCKET_TRANSIENT_UPLOADED_LETTERS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-transient-uploaded-letters"
    S3_BUCKET_PRECOMPILED_ORIGINALS_BACKUP_LETTERS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-precompiled-originals-backup"
    S3_BUCKET_LETTER_ATTACHMENTS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-attachments"
    S3_BUCKET_REPORT_REQUESTS_DOWNLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-report-requests-download"

    LOGO_CDN_DOMAIN = "static-logos.notify.tools"

    ADMIN_CLIENT_SECRET = "dev-notify-secret-key"
    DANGEROUS_SALT = "dev-notify-salt"
    SECRET_KEY = "dev-notify-secret-key"
    API_HOST_NAME = os.environ.get("API_HOST_NAME", "http://localhost:6011")
    ANTIVIRUS_API_HOST = os.environ.get("ANTIVIRUS_API_HOST", "http://localhost:6016")
    ANTIVIRUS_API_KEY = "test-key"
    ANTIVIRUS_ENABLED = os.getenv("ANTIVIRUS_ENABLED") == "1"

    ASSET_PATH = "/static/"

    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    REDIS_ENABLED = os.environ.get("REDIS_ENABLED") == "1"


class TestNL(DevNL):
    NOTIFY_ENVIRONMENT = "test"

    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False

    S3_BUCKET_CSV_UPLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-notifications-csv-upload"
    S3_BUCKET_CONTACT_LIST_UPLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-contact-list"
    S3_BUCKET_LOGO_UPLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-public-logos-tools"
    S3_BUCKET_MOU = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-mou"
    S3_BUCKET_TRANSIENT_UPLOADED_LETTERS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-transient-uploaded-letters"
    S3_BUCKET_PRECOMPILED_ORIGINALS_BACKUP_LETTERS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-precompiled-originals-backup"
    S3_BUCKET_LETTER_ATTACHMENTS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-attachments"
    S3_BUCKET_REPORT_REQUESTS_DOWNLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-report-requests-download"

    LOGO_CDN_DOMAIN = "static-logos.test.com"
    API_HOST_NAME = "http://you-forgot-to-mock-an-api-call-to"
    TEMPLATE_PREVIEW_API_HOST = "http://localhost:9999"
    ANTIVIRUS_API_HOST = "https://test-antivirus"
    ANTIVIRUS_API_KEY = "test-antivirus-secret"
    ANTIVIRUS_ENABLED = True

    ASSET_DOMAIN = "static.example.com"
    ASSET_PATH = "https://static.example.com/"


class AccNL(Config):
    NOTIFY_ENVIRONMENT = "acceptance"

    S3_BUCKET_CSV_UPLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-notifications-csv-upload"
    S3_BUCKET_CONTACT_LIST_UPLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-contact-list"
    S3_BUCKET_LOGO_UPLOAD = f"{NL_PREFIX}-acc-public-logos-tools"
    S3_BUCKET_MOU = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-mou"
    S3_BUCKET_TRANSIENT_UPLOADED_LETTERS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-transient-uploaded-letters"
    S3_BUCKET_PRECOMPILED_ORIGINALS_BACKUP_LETTERS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-precompiled-originals-backup"
    S3_BUCKET_LETTER_ATTACHMENTS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-attachments"
    S3_BUCKET_REPORT_REQUESTS_DOWNLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-report-requests-download"


class ProdNL(Config):
    NOTIFY_ENVIRONMENT = "production"

    S3_BUCKET_CSV_UPLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-notifications-csv-upload"
    S3_BUCKET_CONTACT_LIST_UPLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-contact-list"
    S3_BUCKET_LOGO_UPLOAD = f"{NL_PREFIX}-prod-public-logos-tools"
    S3_BUCKET_MOU = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-mou"
    S3_BUCKET_TRANSIENT_UPLOADED_LETTERS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-transient-uploaded-letters"
    S3_BUCKET_PRECOMPILED_ORIGINALS_BACKUP_LETTERS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-precompiled-originals-backup"
    S3_BUCKET_LETTER_ATTACHMENTS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-attachments"
    S3_BUCKET_REPORT_REQUESTS_DOWNLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-report-requests-download"


configs = {"development": DevNL, "test": Test, "acceptance": AccNL, "production": ProdNL}

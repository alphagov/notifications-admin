import os

if os.environ.get('VCAP_APPLICATION'):
    # on cloudfoundry, config is a json blob in VCAP_APPLICATION - unpack it, and populate
    # standard environment variables from it
    from app.cloudfoundry_config import extract_cloudfoundry_config
    extract_cloudfoundry_config()


class Config(object):
    ADMIN_CLIENT_SECRET = os.environ.get('ADMIN_CLIENT_SECRET')
    API_HOST_NAME = os.environ.get('API_HOST_NAME')
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DANGEROUS_SALT = os.environ.get('DANGEROUS_SALT')
    ZENDESK_API_KEY = os.environ.get('ZENDESK_API_KEY')

    # if we're not on cloudfoundry, we can get to this app from localhost. but on cloudfoundry its different
    ADMIN_BASE_URL = os.environ.get('ADMIN_BASE_URL', 'http://localhost:6012')

    TEMPLATE_PREVIEW_API_HOST = os.environ.get('TEMPLATE_PREVIEW_API_HOST', 'http://localhost:6013')
    TEMPLATE_PREVIEW_API_KEY = os.environ.get('TEMPLATE_PREVIEW_API_KEY', 'my-secret-key')

    # Hosted graphite statsd prefix
    STATSD_PREFIX = os.getenv('STATSD_PREFIX')

    # Logging
    DEBUG = False
    NOTIFY_LOG_PATH = os.getenv('NOTIFY_LOG_PATH')

    ADMIN_CLIENT_USER_NAME = 'notify-admin'

    ANTIVIRUS_API_HOST = os.environ.get('ANTIVIRUS_API_HOST')
    ANTIVIRUS_API_KEY = os.environ.get('ANTIVIRUS_API_KEY')

    ASSETS_DEBUG = False
    AWS_REGION = 'eu-west-1'
    DEFAULT_SERVICE_LIMIT = 50
    DEFAULT_FREE_SMS_FRAGMENT_LIMITS = {
        'central': 250000,
        'local': 25000,
        'nhs': 25000,
    }
    EMAIL_EXPIRY_SECONDS = 3600  # 1 hour
    INVITATION_EXPIRY_SECONDS = 3600 * 24 * 2  # 2 days - also set on api
    EMAIL_2FA_EXPIRY_SECONDS = 1800  # 30 Minutes
    HEADER_COLOUR = '#FFBF47'  # $yellow
    HTTP_PROTOCOL = 'http'
    MAX_FAILED_LOGIN_COUNT = 10
    NOTIFY_APP_NAME = 'admin'
    NOTIFY_LOG_LEVEL = 'DEBUG'
    PERMANENT_SESSION_LIFETIME = 20 * 60 * 60  # 20 hours
    SEND_FILE_MAX_AGE_DEFAULT = 365 * 24 * 60 * 60  # 1 year
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_NAME = 'notify_admin_session'
    SESSION_COOKIE_SECURE = True
    SESSION_REFRESH_EACH_REQUEST = True
    SHOW_STYLEGUIDE = True
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    CSV_UPLOAD_BUCKET_NAME = 'local-notifications-csv-upload'
    ACTIVITY_STATS_LIMIT_DAYS = 7
    TEST_MESSAGE_FILENAME = 'Report'

    STATSD_ENABLED = False
    STATSD_HOST = "statsd.hostedgraphite.com"
    STATSD_PORT = 8125
    NOTIFY_ENVIRONMENT = 'development'
    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-local'
    MOU_BUCKET_NAME = 'local-mou'
    ROUTE_SECRET_KEY_1 = os.environ.get('ROUTE_SECRET_KEY_1', '')
    ROUTE_SECRET_KEY_2 = os.environ.get('ROUTE_SECRET_KEY_2', '')
    CHECK_PROXY_HEADER = False

    REDIS_URL = os.environ.get('REDIS_URL')
    REDIS_ENABLED = os.environ.get('REDIS_ENABLED') == '1'


class Development(Config):
    NOTIFY_LOG_PATH = 'application.log'
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SESSION_PROTECTION = None
    STATSD_ENABLED = False
    CSV_UPLOAD_BUCKET_NAME = 'development-notifications-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-tools'
    MOU_BUCKET_NAME = 'notify.tools-mou'

    ADMIN_CLIENT_SECRET = 'dev-notify-secret-key'
    API_HOST_NAME = 'http://localhost:6011'
    DANGEROUS_SALT = 'dev-notify-salt'
    SECRET_KEY = 'dev-notify-secret-key'
    ANTIVIRUS_API_HOST = 'http://localhost:6016'
    ANTIVIRUS_API_KEY = 'test-key'


class Test(Development):
    DEBUG = True
    TESTING = True
    STATSD_ENABLED = False
    WTF_CSRF_ENABLED = False
    CSV_UPLOAD_BUCKET_NAME = 'test-notifications-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-test'
    MOU_BUCKET_NAME = 'test-mou'
    NOTIFY_ENVIRONMENT = 'test'
    API_HOST_NAME = 'http://you-forgot-to-mock-an-api-call-to'
    TEMPLATE_PREVIEW_API_HOST = 'http://localhost:9999'
    ANTIVIRUS_API_HOST = 'https://test-antivirus'
    ANTIVIRUS_API_KEY = 'test-antivirus-secret'


class Preview(Config):
    HTTP_PROTOCOL = 'https'
    HEADER_COLOUR = '#F499BE'  # $baby-pink
    STATSD_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'preview-notifications-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-preview'
    MOU_BUCKET_NAME = 'notify.works-mou'
    NOTIFY_ENVIRONMENT = 'preview'
    CHECK_PROXY_HEADER = False


class Staging(Config):
    SHOW_STYLEGUIDE = False
    HTTP_PROTOCOL = 'https'
    HEADER_COLOUR = '#6F72AF'  # $mauve
    STATSD_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'staging-notify-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-staging'
    MOU_BUCKET_NAME = 'staging-notify.works-mou'
    NOTIFY_ENVIRONMENT = 'staging'
    CHECK_PROXY_HEADER = False


class Live(Config):
    SHOW_STYLEGUIDE = False
    HEADER_COLOUR = '#005EA5'  # $govuk-blue
    HTTP_PROTOCOL = 'https'
    STATSD_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'live-notifications-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-production'
    MOU_BUCKET_NAME = 'notifications.service.gov.uk-mou'
    NOTIFY_ENVIRONMENT = 'live'
    CHECK_PROXY_HEADER = False


class CloudFoundryConfig(Config):
    pass


# CloudFoundry sandbox
class Sandbox(CloudFoundryConfig):
    HTTP_PROTOCOL = 'https'
    HEADER_COLOUR = '#F499BE'  # $baby-pink
    STATSD_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'cf-sandbox-notifications-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'cf-sandbox-notifications-logo-upload'
    NOTIFY_ENVIRONMENT = 'sandbox'


configs = {
    'development': Development,
    'test': Test,
    'preview': Preview,
    'staging': Staging,
    'live': Live,
    'production': Live,
    'sandbox': Sandbox
}

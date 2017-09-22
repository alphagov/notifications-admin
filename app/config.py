import os
from datetime import timedelta


if os.environ.get('VCAP_SERVICES'):
    # on cloudfoundry, config is a json blob in VCAP_SERVICES - unpack it, and populate
    # standard environment variables from it
    from app.cloudfoundry_config import extract_cloudfoundry_config
    extract_cloudfoundry_config()


class Config(object):
    ADMIN_CLIENT_SECRET = os.environ['ADMIN_CLIENT_SECRET']
    API_HOST_NAME = os.environ['API_HOST_NAME']
    SECRET_KEY = os.environ['SECRET_KEY']
    DANGEROUS_SALT = os.environ['DANGEROUS_SALT']
    DESKPRO_API_HOST = os.environ['DESKPRO_API_HOST']
    DESKPRO_API_KEY = os.environ['DESKPRO_API_KEY']

    # if we're not on cloudfoundry, we can get to this app from localhost. but on cloudfoundry its different
    ADMIN_BASE_URL = os.environ.get('ADMIN_BASE_URL', 'http://localhost:6012')

    TEMPLATE_PREVIEW_API_HOST = os.environ.get('TEMPLATE_PREVIEW_API_HOST', 'http://localhost:6013')
    TEMPLATE_PREVIEW_API_KEY = os.environ.get('TEMPLATE_PREVIEW_API_KEY', 'my-secret-key')

    # Hosted graphite statsd prefix
    STATSD_PREFIX = os.getenv('STATSD_PREFIX')

    # Logging
    DEBUG = False
    NOTIFY_LOG_PATH = os.getenv('NOTIFY_LOG_PATH')

    DESKPRO_DEPT_ID = 5
    DESKPRO_ASSIGNED_AGENT_TEAM_ID = 5

    ADMIN_CLIENT_USER_NAME = 'notify-admin'
    ASSETS_DEBUG = False
    AWS_REGION = 'eu-west-1'
    DEFAULT_SERVICE_LIMIT = 50
    EMAIL_EXPIRY_SECONDS = 3600 * 24 * 7  # one week
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
    # TODO: move to utils
    SMS_CHAR_COUNT_LIMIT = 459
    TOKEN_MAX_AGE_SECONDS = 3600
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    CSV_UPLOAD_BUCKET_NAME = 'local-notifications-csv-upload'
    DESKPRO_PERSON_EMAIL = 'donotreply@notifications.service.gov.uk'
    ACTIVITY_STATS_LIMIT_DAYS = 7
    TEST_MESSAGE_FILENAME = 'Report'

    STATSD_ENABLED = False
    STATSD_HOST = "statsd.hostedgraphite.com"
    STATSD_PORT = 8125
    NOTIFY_ENVIRONMENT = 'development'

    EMAIL_DOMAIN_REGEXES = [
        r"gov\.uk",
        r"mod\.uk",
        r"mil\.uk",
        r"ddc-mod\.org",
        r"slc\.co\.uk",
        r"gov\.scot",
        r"parliament\.uk",
        r"nhs\.uk",
        r"nhs\.net",
        r"police\.uk",
        r"dclgdatamart\.co\.uk",
        r"ucds\.email",
        r"naturalengland\.org\.uk",
        r"hmcts\.net",
        r"scotent\.co\.uk",
        r"assembly\.wales",
        r"cjsm\.net",
        r"cqc\.org\.uk",
        r"bl\.uk",
        r"stfc\.ac\.uk",
        r"wmfs\.net",
        r"bbsrc\.ac\.uk",
    ]

    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-local'


class Development(Config):
    NOTIFY_LOG_PATH = 'application.log'
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SESSION_PROTECTION = None
    STATSD_ENABLED = False
    CSV_UPLOAD_BUCKET_NAME = 'development-notifications-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-tools'


class Test(Development):
    DEBUG = True
    TESTING = True
    STATSD_ENABLED = True
    WTF_CSRF_ENABLED = False
    CSV_UPLOAD_BUCKET_NAME = 'test-notifications-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-test'
    NOTIFY_ENVIRONMENT = 'test'
    TEMPLATE_PREVIEW_API_HOST = 'http://localhost:9999'


class Preview(Config):
    HTTP_PROTOCOL = 'https'
    HEADER_COLOUR = '#F499BE'  # $baby-pink
    STATSD_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'preview-notifications-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-preview'
    NOTIFY_ENVIRONMENT = 'preview'


class Staging(Config):
    SHOW_STYLEGUIDE = False
    HTTP_PROTOCOL = 'https'
    HEADER_COLOUR = '#6F72AF'  # $mauve
    STATSD_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'staging-notify-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-staging'
    NOTIFY_ENVIRONMENT = 'staging'


class Live(Config):
    SHOW_STYLEGUIDE = False
    HEADER_COLOUR = '#005EA5'  # $govuk-blue
    HTTP_PROTOCOL = 'https'
    STATSD_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'live-notifications-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-production'
    NOTIFY_ENVIRONMENT = 'live'


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

import os
from datetime import timedelta


class Config(object):
    ADMIN_CLIENT_SECRET = os.environ['ADMIN_CLIENT_SECRET']
    API_HOST_NAME = os.environ['API_HOST_NAME']
    SECRET_KEY = os.environ['SECRET_KEY']
    DANGEROUS_SALT = os.environ['DANGEROUS_SALT']
    DESKPRO_API_HOST = os.environ['DESKPRO_API_HOST']
    DESKPRO_API_KEY = os.environ['DESKPRO_API_KEY']
    # Hosted graphite statsd prefix
    STATSD_PREFIX = os.getenv('STATSD_PREFIX')

    DESKPRO_DEPT_ID = 5
    DESKPRO_ASSIGNED_AGENT_TEAM_ID = 5

    DEBUG = False
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
    NOTIFY_LOG_PATH = '/var/log/notify/application.log'
    PERMANENT_SESSION_LIFETIME = 3600  # seconds
    REMEMBER_COOKIE_DURATION = timedelta(days=1)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_NAME = 'notify_admin_remember_me'
    REMEMBER_COOKIE_SECURE = True
    SEND_FILE_MAX_AGE_DEFAULT = 365 * 24 * 60 * 60  # 1 year
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_NAME = 'notify_admin_session'
    SESSION_COOKIE_SECURE = True
    SESSION_REFRESH_EACH_REQUEST = True
    SHOW_STYLEGUIDE = True
    TOKEN_MAX_AGE_SECONDS = 3600
    WTF_CSRF_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'local-notifications-csv-upload'
    DESKPRO_PERSON_EMAIL = 'donotreply@notifications.service.gov.uk'
    ACTIVITY_STATS_LIMIT_DAYS = 7
    TEST_MESSAGE_FILENAME = 'Test message'

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
        r"kainos\.com",
        r"salesforce\.com",
        r"bitzesty\.com",
        r"dclgdatamart\.co\.uk",
        r"valtech\.co\.uk",
        r"cgi\.com",
        r"capita\.co\.uk",
        r"ucds\.email"
    ]


class Development(Config):
    DEBUG = True
    REMEMBER_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False
    SESSION_PROTECTION = None
    STATSD_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'development-notifications-csv-upload'


class Test(Development):
    DEBUG = True
    STATSD_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'test-notifications-csv-upload'
    NOTIFY_ENVIRONMENT = 'test'


class Preview(Config):
    HTTP_PROTOCOL = 'https'
    HEADER_COLOUR = '#F499BE'  # $baby-pink
    STATSD_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'preview-notifications-csv-upload'
    NOTIFY_ENVIRONMENT = 'preview'


class Staging(Config):
    SHOW_STYLEGUIDE = False
    HTTP_PROTOCOL = 'https'
    HEADER_COLOUR = '#6F72AF'  # $mauve
    STATSD_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'staging-notify-csv-upload'
    NOTIFY_ENVIRONMENT = 'staging'


class Live(Config):
    SHOW_STYLEGUIDE = False
    HEADER_COLOUR = '#005EA5'  # $govuk-blue
    HTTP_PROTOCOL = 'https'
    STATSD_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'live-notifications-csv-upload'
    NOTIFY_ENVIRONMENT = 'live'


configs = {
    'development': Development,
    'test': Test,
    'preview': Preview,
    'staging': Staging,
    'live': Live
}

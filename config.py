import os
from datetime import timedelta


class Config(object):
    ADMIN_CLIENT_SECRET = os.environ['ADMIN_CLIENT_SECRET']
    API_HOST_NAME = os.environ['API_HOST_NAME']
    SECRET_KEY = os.environ['SECRET_KEY']
    DANGEROUS_SALT = os.environ['DANGEROUS_SALT']
    DESKPRO_API_HOST = os.environ['DESKPRO_API_HOST']
    DESKPRO_API_KEY = os.environ['DESKPRO_API_KEY']

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

    EMAIL_DOMAIN_REGEXES = [
        "gov\.uk",
        "mod\.uk",
        "mil\.uk",
        "ddc-mod\.org",
        "slc\.co\.uk",
        "gov\.scot",
        "parliament\.uk",
        "nhs\.uk",
        "nhs\.net",
        "police\.uk",
        "kainos\.com",
        "salesforce\.com",
        "bitzesty\.com",
        "dclgdatamart\.co\.uk",
        "valtech\.co\.uk",
        "gofreerange\.com",
        "cgi\.com",
        "unboxed\.com",
        "capita\.co\.uk"]


class Development(Config):
    DEBUG = True
    REMEMBER_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False
    SESSION_PROTECTION = None
    CSV_UPLOAD_BUCKET_NAME = 'development-notifications-csv-upload'


class Test(Development):
    DEBUG = True
    CSV_UPLOAD_BUCKET_NAME = 'test-notifications-csv-upload'


class Preview(Config):
    HTTP_PROTOCOL = 'https'
    HEADER_COLOUR = '#F47738'  # $orange
    CSV_UPLOAD_BUCKET_NAME = 'preview-notifications-csv-upload'


class Staging(Config):
    SHOW_STYLEGUIDE = False
    HTTP_PROTOCOL = 'https'
    HEADER_COLOUR = '#F47738'  # $orange
    CSV_UPLOAD_BUCKET_NAME = 'staging-notify-csv-upload'


class Live(Config):
    SHOW_STYLEGUIDE = False
    HEADER_COLOUR = '#B10E1E'  # $red
    HTTP_PROTOCOL = 'https'
    CSV_UPLOAD_BUCKET_NAME = 'live-notifications-csv-upload'


configs = {
    'development': Development,
    'test': Test,
    'preview': Preview,
    'staging': Staging,
    'live': Live
}

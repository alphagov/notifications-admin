import os
from datetime import timedelta


class Config(object):

    DEBUG = False
    ADMIN_CLIENT_SECRET = os.environ['ADMIN_CLIENT_SECRET']
    ADMIN_CLIENT_USER_NAME = os.environ['ADMIN_CLIENT_USER_NAME']
    API_HOST_NAME = os.environ['API_HOST_NAME']
    ASSETS_DEBUG = False
    AWS_REGION = 'eu-west-1'
    DANGEROUS_SALT = os.environ['DANGEROUS_SALT']
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
    REMEMBER_COOKIE_PATH = '/admin'
    REMEMBER_COOKIE_SECURE = True
    SECRET_KEY = os.environ['SECRET_KEY']
    SEND_FILE_MAX_AGE_DEFAULT = 365 * 24 * 60 * 60  # 1 year
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_NAME = 'notify_admin_session'
    SESSION_COOKIE_PATH = '/admin'
    SESSION_COOKIE_SECURE = True
    SESSION_REFRESH_EACH_REQUEST = True
    SHOW_STYLEGUIDE = True
    TOKEN_MAX_AGE_SECONDS = 3600
    WTF_CSRF_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'local-notifications-csv-upload'

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
        "police\.uk"]


class Development(Config):
    DEBUG = True
    REMEMBER_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False
    CSV_UPLOAD_BUCKET_NAME = 'development-notifications-csv-upload'


class Test(Development):
    DEBUG = True
    CSV_UPLOAD_BUCKET_NAME = 'test-notifications-csv-upload'


class Preview(Config):
    HTTP_PROTOCOL = 'https'
    HEADER_COLOUR = '#F47738'  # $orange
    CSV_UPLOAD_BUCKET_NAME = 'preview-notifications-csv-upload'


configs = {
    'development': 'config.Development',
    'test': 'config.Test',
    'preview': 'config.Preview',
    'staging': 'config_staging.Staging',
    'live': 'config_live.Live'
}

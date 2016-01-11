import os


class Config(object):
    DEBUG = False
    ASSETS_DEBUG = False
    cache = False
    manifest = True

    NOTIFY_LOG_LEVEL = 'DEBUG'
    NOTIFY_APP_NAME = 'admin'
    NOTIFY_LOG_PATH = '/var/log/notify/application.log'

    SQLALCHEMY_COMMIT_ON_TEARDOWN = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/notifications_admin'
    MAX_FAILED_LOGIN_COUNT = 10
    PASS_SECRET_KEY = 'secret-key-unique-changeme'

    SESSION_COOKIE_NAME = 'notify_admin_session'
    SESSION_COOKIE_PATH = '/admin'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True

    NOTIFY_DATA_API_URL = os.getenv('NOTIFY_API_URL', "http://localhost:6001")
    NOTIFY_DATA_API_AUTH_TOKEN = os.getenv('NOTIFY_API_TOKEN', "dev-token")

    WTF_CSRF_ENABLED = True
    SECRET_KEY = 'secret-key'
    HTTP_PROTOCOL = 'http'
    DANGEROUS_SALT = 'itsdangeroussalt'
    TOKEN_MAX_AGE_SECONDS = 120000

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10mb


class Development(Config):
    DEBUG = True


class Test(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/test_notifications_admin'
    WTF_CSRF_ENABLED = False


class Live(Config):
    DEBUG = False
    HTTP_PROTOCOL = 'https'

configs = {
    'live': Live,
    'development': Development,
    'test': Test
}

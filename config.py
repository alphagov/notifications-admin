
class Config(object):
    DEBUG = False
    ASSETS_DEBUG = False
    cache = False
    manifest = True

    SQLALCHEMY_COMMIT_ON_TEARDOWN = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/notifications_admin'
    MAX_FAILED_LOGIN_COUNT = 10
    SECRET_KEY = 'secret-key-unique-changeme'


class Development(Config):
    DEBUG = True


class Test(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/test_notifications_admin'


configs = {
    'development': Development,
    'test': Test
}

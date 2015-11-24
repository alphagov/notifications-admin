
class Config(object):
    DEBUG = False
    ASSETS_DEBUG = False
    cache = False
    manifest = True


class Development(Config):
    DEBUG = True


class Test(Config):
    DEBUG = False


configs = {
    'development': Development,
    'TEST': Test
}

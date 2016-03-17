import os
from config import Config


class Live(Config):
    SHOW_STYLEGUIDE = False
    HEADER_COLOUR = '#B10E1E'  # $red
    HTTP_PROTOCOL = 'https'
    API_HOST_NAME = os.getenv('LIVE_API_HOST_NAME')
    NOTIFY_API_SECRET = os.getenv('LIVE_NOTIFY_API_SECRET', "dev-secret")
    NOTIFY_API_CLIENT = os.getenv('LIVE_NOTIFY_API_CLIENT', "admin")
    ADMIN_CLIENT_USER_NAME = os.getenv('LIVE_ADMIN_CLIENT_USER_NAME')
    ADMIN_CLIENT_SECRET = os.getenv('LIVE_ADMIN_CLIENT_SECRET')
    SECRET_KEY = os.getenv('LIVE_SECRET_KEY')
    DANGEROUS_SALT = os.getenv('LIVE_DANGEROUS_SALT')

import os
from config import Config


class Live(Config):
    SHOW_STYLEGUIDE = False
    HEADER_COLOUR = '#B10E1E'  # $red
    HTTP_PROTOCOL = 'https'
    API_HOST_NAME = os.environ['LIVE_API_HOST_NAME']
    ADMIN_CLIENT_SECRET = os.environ['LIVE_ADMIN_CLIENT_SECRET']
    SECRET_KEY = os.environ['LIVE_SECRET_KEY']
    DANGEROUS_SALT = os.environ['LIVE_DANGEROUS_SALT']

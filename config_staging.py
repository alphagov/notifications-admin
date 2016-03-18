import os
from config import Config


class Staging(Config):
    SHOW_STYLEGUIDE = False
    HTTP_PROTOCOL = 'https'
    API_HOST_NAME = os.getenv('STAGING_API_HOST_NAME')
    ADMIN_CLIENT_SECRET = os.getenv('STAGING_ADMIN_CLIENT_SECRET')
    SECRET_KEY = os.getenv('STAGING_SECRET_KEY')
    DANGEROUS_SALT = os.getenv('STAGING_DANGEROUS_SALT')

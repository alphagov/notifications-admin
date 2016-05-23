import os
from config import Config


class Staging(Config):
    SHOW_STYLEGUIDE = False
    HTTP_PROTOCOL = 'https'
    API_HOST_NAME = os.environ['STAGING_API_HOST_NAME']
    ADMIN_CLIENT_SECRET = os.environ['STAGING_ADMIN_CLIENT_SECRET']
    SECRET_KEY = os.environ['STAGING_SECRET_KEY']
    DANGEROUS_SALT = os.environ['STAGING_DANGEROUS_SALT']
    CSV_UPLOAD_BUCKET_NAME = 'staging-notifications-csv-upload'
    DESKPRO_API_KEY = os.environ['STAGING_DESKPRO_API_KEY']
    DESKPRO_DEPT_ID = os.environ['STAGING_DESKPRO_DEPT_ID']
    DESKPRO_ASSIGNED_AGENT_TEAM_ID = os.environ['STAGING_DESKPRO_ASSIGNED_AGENT_TEAM_ID']

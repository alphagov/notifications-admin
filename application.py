import os

import sentry_sdk
from flask import Flask
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations import logging

from app import create_app

sentry_sdk.init(
    dsn=os.environ['SENTRY_DSN'],
    integrations=[FlaskIntegration(), RedisIntegration()],
    environment=os.environ['NOTIFY_ENVIRONMENT'],
    attach_stacktrace=True,
    traces_sample_rate=0.00005  # avoid exceeding rate limits in Production
)

sentry_sdk.set_level('error')  # only record error logs or exceptions
logging.ignore_logger('notifications_python_client.*')  # ignore logs about 404s, etc.

application = Flask('app')

create_app(application)

import os

from app.performance import init_performance_monitoring

init_performance_monitoring()

from flask import Flask  # noqa
from app import create_app  # noqa

from notifications_utils.eventlet import EventletTimeoutMiddleware, using_eventlet  # noqa

application = Flask("app")

create_app(application)

if using_eventlet:
    application.wsgi_app = EventletTimeoutMiddleware(
        application.wsgi_app,
        timeout_seconds=int(os.getenv("HTTP_SERVE_TIMEOUT_SECONDSS", 30)),
    )

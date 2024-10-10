from app.performance import init_performance_monitoring

init_performance_monitoring()

from flask import Flask  # noqa
from app import create_app  # noqa

from notifications_utils.eventlet import EventletTimeoutMiddleware, using_eventlet  # noqa

application = Flask("app")

create_app(application)

if using_eventlet:
    application = EventletTimeoutMiddleware(application, timeout_seconds=60)

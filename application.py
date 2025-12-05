import os

from app.performance import init_performance_monitoring

init_performance_monitoring()

from flask import Flask  # noqa
from app import create_app  # noqa

import notifications_utils.eventlet as utils_eventlet  # noqa

application = Flask("app")

create_app(application)

if utils_eventlet.using_eventlet:
    http_serve_timeout_seconds = int(os.getenv("HTTP_SERVE_TIMEOUT_SECONDS", 30))
    application.wsgi_app = utils_eventlet.EventletTimeoutMiddleware(
        application.wsgi_app,
        timeout_seconds=http_serve_timeout_seconds,
        soft_timeout_seconds=http_serve_timeout_seconds - 1,
    )

    if application.config["NOTIFY_EVENTLET_STATS"]:
        import greenlet

        greenlet.settrace(utils_eventlet.account_greenlet_times)
        application._server_greenlet = greenlet.getcurrent()

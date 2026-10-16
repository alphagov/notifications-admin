import os

import notifications_utils.greenlet as utils_greenlet

from app.performance import init_performance_monitoring

init_performance_monitoring()

from flask import Flask  # noqa
from app import create_app  # noqa

application = Flask("app")

create_app(application)

if utils_greenlet.using_eventlet or utils_greenlet.using_gevent:
    http_serve_timeout_seconds = int(os.getenv("HTTP_SERVE_TIMEOUT_SECONDS", 30))
    application.wsgi_app = utils_greenlet.RequestHandlingTimeoutMiddleware(
        application.wsgi_app,
        timeout_seconds=http_serve_timeout_seconds,
        soft_timeout_seconds=http_serve_timeout_seconds - 1,
    )

    if application.config["NOTIFY_GREENLET_STATS"]:
        import greenlet

        greenlet.settrace(utils_greenlet.account_greenlet_times)
        application._server_greenlet = greenlet.getcurrent()

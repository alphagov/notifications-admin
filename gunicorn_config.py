import os

from gds_metrics.gunicorn import child_exit  # noqa
from notifications_utils.gunicorn_defaults import set_gunicorn_defaults

set_gunicorn_defaults(globals())

workers = 5
worker_class = "eventlet"
keepalive = 35
timeout = int(os.getenv("HTTP_SERVE_TIMEOUT_SECONDS", 30))  # though has little effect with eventlet worker_class

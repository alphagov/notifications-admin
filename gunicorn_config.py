import os

from notifications_utils.gunicorn.defaults import set_gunicorn_defaults

set_gunicorn_defaults(globals())

workers = 5
worker_class = "notifications_utils.gunicorn.eventlet.OtelAwareEventletWorker"
keepalive = 35
timeout = int(os.getenv("HTTP_SERVE_TIMEOUT_SECONDS", 30))  # though has little effect with eventlet worker_class

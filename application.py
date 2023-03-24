from app.performance import init_performance_monitoring

init_performance_monitoring()

from flask import Flask  # noqa

from app import create_app  # noqa

application = Flask("app")

create_app(application)

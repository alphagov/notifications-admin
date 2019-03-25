from flask import Blueprint

from app.status.views import healthcheck  # noqa

status = Blueprint('status', __name__)

from flask import g, has_request_context, request
from flask_login import current_user
from notifications_python_client import __version__
from notifications_python_client.base import BaseAPIClient
from notifications_utils.clients.redis import RequestCache

from app.extensions import redis_client

cache = RequestCache(redis_client)


def _attach_current_user(data):
    return dict(created_by=current_user.id, **data)


class NotifyAdminAPIClient(BaseAPIClient):
    def __init__(self):
        super().__init__("a" * 73, "b")

    def init_app(self, app):
        self.base_url = app.config["API_HOST_NAME"]
        self.service_id = app.config["ADMIN_CLIENT_USER_NAME"]
        self.api_key = app.config["ADMIN_CLIENT_SECRET"]
        self.route_secret = app.config["ROUTE_SECRET_KEY_1"]

    def generate_headers(self, api_token):
        headers = {
            "Content-type": "application/json",
            "Authorization": "Bearer {}".format(api_token),
            "X-Custom-Forwarder": self.route_secret,
            "User-agent": "NOTIFY-API-PYTHON-CLIENT/{}".format(__version__),
        }
        return self._add_request_id_header(headers)

    @staticmethod
    def _add_request_id_header(headers):
        if not has_request_context():
            return headers

        headers["X-B3-TraceId"] = request.request_id
        headers["X-B3-SpanId"] = request.span_id

        if g.user_id:
            headers["X-Notify-User-Id"] = g.user_id

        return headers


class InviteTokenError(Exception):
    pass

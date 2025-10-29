from contextvars import ContextVar

import requests
from flask import g, has_request_context, request
from flask_login import current_user
from notifications_python_client import __version__
from notifications_python_client.base import BaseAPIClient
from notifications_utils.clients.redis import RequestCache
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.extensions import redis_client

cache = RequestCache(redis_client)


_api_client_request_session_context_var: ContextVar[requests.Session] = ContextVar("api_client_request_session")
get_api_client_request_session: LazyLocalGetter[requests.Session] = LazyLocalGetter(
    _api_client_request_session_context_var,
    lambda: requests.Session(),
)
memo_resetters.append(lambda: get_api_client_request_session.clear())
api_client_request_session = LocalProxy(get_api_client_request_session)


def _attach_current_user(data):
    return dict(created_by=current_user.id, **data)


class NotifyAdminAPIClient(BaseAPIClient):
    def __init__(self, app, *args, **kwargs):
        try:
            base_url = app.config["API_HOST_NAME"]
        except RuntimeError as e:
            raise RuntimeError(
                "Could not teardown fixtures after test run. Try: \n"
                "• moving `mocker` so it’s the final argument to your test function. \n"
                "• running pytest with the `--setup-show` flag to see which fixture is the problem"
            ) from e

        super().__init__(
            "x" * 100,
            *args,
            base_url=base_url,
            **kwargs,
        )
        # our credential lengths aren't what BaseAPIClient's __init__ will expect
        # given it's designed for destructuring end-user api keys
        self.service_id = app.config["ADMIN_CLIENT_USER_NAME"]
        self.api_key = app.config["ADMIN_CLIENT_SECRET"]

    def generate_headers(self, api_token):
        headers = {
            "Content-type": "application/json",
            "Authorization": f"Bearer {api_token}",
            "User-agent": f"NOTIFY-API-PYTHON-CLIENT/{__version__}",
        }
        if has_request_context():
            if hasattr(request, "get_onwards_request_headers"):
                headers = {
                    **request.get_onwards_request_headers(),
                    **headers,
                }
            if g.user_id:
                headers["X-Notify-User-Id"] = g.user_id

        return headers


class InviteTokenError(Exception):
    pass

from flask_login import current_user
from flask import has_request_context, request
from notifications_python_client.base import BaseAPIClient
from notifications_python_client.version import __version__


def _attach_current_user(data):
    return dict(
        created_by=current_user.id,
        **data
    )


class NotifyAdminAPIClient(BaseAPIClient):
    def generate_headers(self, api_token):
        headers = {
            "Content-type": "application/json",
            "Authorization": "Bearer {}".format(api_token),
            "User-agent": "NOTIFY-API-PYTHON-CLIENT/{}".format(__version__)
        }
        return self._add_request_id_header(headers)

    @staticmethod
    def _add_request_id_header(headers):
        if not has_request_context():
            return headers
        headers['NotifyRequestID'] = request.request_id
        return headers

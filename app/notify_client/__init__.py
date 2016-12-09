from flask_login import current_user
from flask import has_request_context, request, abort
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

    def check_inactive_service(self):
        # this file is imported in app/__init__.py before current_service is initialised, so need to import later
        # to prevent cyclical imports
        from app import current_service

        # if the current service is inactive and the user isn't a platform admin, we should block them from making any
        # stateful modifications to that service
        print('\n\n\n')
        print(current_service)
        print(current_user)
        if current_service and not current_service['active'] and not current_user.platform_admin:
            abort(403)


    def post(self, *args, **kwargs):
        self.check_inactive_service()
        return super().post(*args, **kwargs)

    def put(self, *args, **kwargs):
        self.check_inactive_service()
        return super().put(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.check_inactive_service()
        return super().delete(*args, **kwargs)

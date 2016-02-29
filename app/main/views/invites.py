from flask import (
    redirect,
    url_for,
    abort
)

from notifications_python_client.errors import HTTPError

from app.main import main
from app import (
    invite_api_client,
    user_api_client
)


@main.route("/invitation/<token>")
def accept_invite(token):
    try:
        invited_user = invite_api_client.accept_invite(token)
        existing_user = user_api_client.get_user_by_email(invited_user['email_address'])

        if existing_user:
            user_api_client.add_user_to_service(invited_user['service'],
                                                existing_user.id,
                                                invited_user)
            return redirect(url_for('main.service_dashboard', service_id=invited_user['service']))
        else:
            # TODO implement registration flow for new users
            abort(404)
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e

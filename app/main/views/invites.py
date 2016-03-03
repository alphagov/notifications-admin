from flask import (
    redirect,
    url_for,
    session,
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

        invited_user = invite_api_client.check_token(token)
        existing_user = user_api_client.get_user_by_email(invited_user.email_address)

        if existing_user:
            user_api_client.add_user_to_service(invited_user.service,
                                                existing_user.id,
                                                invited_user.permissions)
            invite_api_client.accept_invite(invited_user.service, invited_user.id)
            return redirect(url_for('main.service_dashboard', service_id=invited_user.service))
        else:
            session['invited_user'] = invited_user.serialize()
            return redirect(url_for('main.register_from_invite'))

    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e

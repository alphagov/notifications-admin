from flask import (
    redirect,
    url_for,
    session
)

from app.main import main
from app import (
    invite_api_client,
    user_api_client
)


@main.route("/invitation/<token>")
def accept_invite(token):

    invited_user = invite_api_client.accept_invite(token)
    existing_user = user_api_client.get_user_by_email(invited_user.email_address)

    if existing_user:
        user_api_client.add_user_to_service(invited_user.service,
                                            existing_user.id,
                                            invited_user)
        return redirect(url_for('main.service_dashboard', service_id=invited_user.service))
    else:
        session['invited_user'] = invited_user.serialize()
        return redirect(url_for('main.register_from_invite'))

from flask import (
    redirect,
    url_for,
    session,
    render_template
)


from app.main import main
from app.main.dao.services_dao import get_service_by_id_or_404
from app import (
    invite_api_client,
    user_api_client
)


@main.route("/invitation/<token>")
def accept_invite(token):
    invited_user = invite_api_client.check_token(token)
    if invited_user.status == 'cancelled':
        from_user = user_api_client.get_user(invited_user.from_user)
        service = get_service_by_id_or_404(invited_user.service)
        return render_template('views/cancelled-invitation.html',
                               from_user=from_user.name,
                               service_name=service['name'])

    existing_user = user_api_client.get_user_by_email(invited_user.email_address)
    session['invited_user'] = invited_user.serialize()

    if existing_user:

        user_api_client.add_user_to_service(invited_user.service,
                                            existing_user.id,
                                            invited_user.permissions)
        invite_api_client.accept_invite(invited_user.service, invited_user.id)
        return redirect(url_for('main.service_dashboard', service_id=invited_user.service))
    else:
        return redirect(url_for('main.register_from_invite'))

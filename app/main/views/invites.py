from flask import (
    redirect,
    url_for,
    session,
    flash,
    render_template
)


from notifications_python_client.errors import HTTPError

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

    if invited_user.status == 'accepted':
        session.pop('invited_user', None)
        flash('You have already accepted this invitation', 'default')
        return redirect(url_for('main.service_dashboard', service_id=invited_user.service))

    session['invited_user'] = invited_user.serialize()

    try:
        existing_user = user_api_client.get_user_by_email(invited_user.email_address)
    except HTTPError as ex:
        if ex.status_code == 404:
            existing_user = False

    service_users = user_api_client.get_users_for_service(invited_user.service)

    if existing_user:
        if existing_user in service_users:
            session.pop('invited_user', None)
            flash('You have already accepted an invitation to this service', 'default')
            invite_api_client.accept_invite(invited_user.service, invited_user.id)
            return redirect(url_for('main.service_dashboard', service_id=invited_user.service))
        else:
            user_api_client.add_user_to_service(invited_user.service,
                                                existing_user.id,
                                                invited_user.permissions)
            invite_api_client.accept_invite(invited_user.service, invited_user.id)
            return redirect(url_for('main.service_dashboard', service_id=invited_user.service))
    else:
        return redirect(url_for('main.register_from_invite'))

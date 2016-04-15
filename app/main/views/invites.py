from flask import (
    redirect,
    url_for,
    session,
    flash,
    render_template,
    abort
)

from app.main import main

from app import (
    invite_api_client,
    user_api_client,
    service_api_client
)

from flask_login import current_user


@main.route("/invitation/<token>")
def accept_invite(token):

    invited_user = invite_api_client.check_token(token)

    if not current_user.is_anonymous() and current_user.email_address != invited_user.email_address:
        flash("""
            You’re signed in as {}.
            This invite is for another email address.
            <a href='{}'>Sign out</a> and click the link again to accept this invite.
        """.format(
            current_user.email_address,
            url_for("main.sign_out")
        ))
        abort(403)

    if invited_user.status == 'cancelled':
        from_user = user_api_client.get_user(invited_user.from_user)
        service = service_api_client.get_service(invited_user.service)['data']
        return render_template('views/cancelled-invitation.html',
                               from_user=from_user.name,
                               service_name=service['name'])

    if invited_user.status == 'accepted':
        session.pop('invited_user', None)
        return redirect(url_for('main.service_dashboard', service_id=invited_user.service))

    session['invited_user'] = invited_user.serialize()

    existing_user = user_api_client.get_user_by_email_or_none(invited_user.email_address)
    service_users = user_api_client.get_users_for_service(invited_user.service)

    if existing_user:
        if existing_user in service_users:
            return redirect(url_for('main.service_dashboard', service_id=invited_user.service))
        else:
            user_api_client.add_user_to_service(invited_user.service,
                                                existing_user.id,
                                                invited_user.permissions)
            return redirect(url_for('main.service_dashboard', service_id=invited_user.service))
    else:
        return redirect(url_for('main.register_from_invite'))

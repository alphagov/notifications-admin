from flask import abort, flash, redirect, render_template, session, url_for
from flask_login import current_user
from markupsafe import Markup
from notifications_python_client.errors import HTTPError

from app import (
    invite_api_client,
    org_invite_api_client,
    organisations_client,
    service_api_client,
    user_api_client,
)
from app.main import main


@main.route("/invitation/<token>")
def accept_invite(token):
    try:
        invited_user = invite_api_client.check_token(token)
    except HTTPError as e:
        if e.status_code == 400 and 'invitation' in e.message:
            flash(e.message['invitation'])
            return redirect(url_for('main.sign_in'))
        else:
            raise e

    if not current_user.is_anonymous and current_user.email_address.lower() != invited_user.email_address.lower():
        message = Markup("""
            You’re signed in as {}.
            This invite is for another email address.
            <a href={}>Sign out</a> and click the link again to accept this invite.
            """.format(
            current_user.email_address,
            url_for("main.sign_out", _external=True)))

        flash(message=message)

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
        invite_api_client.accept_invite(invited_user.service, invited_user.id)
        if existing_user in service_users:
            return redirect(url_for('main.service_dashboard', service_id=invited_user.service))
        else:
            service = service_api_client.get_service(invited_user.service)['data']
            # if the service you're being added to can modify auth type, then check if this is relevant
            if 'email_auth' in service['permissions'] and (
                    # they have a phone number, we want them to start using it. if they dont have a mobile we just
                    # ignore that option of the invite
                    (existing_user.mobile_number and invited_user.auth_type == 'sms_auth') or
                    # we want them to start sending emails. it's always valid, so lets always update
                    invited_user.auth_type == 'email_auth'
            ):
                user_api_client.update_user_attribute(existing_user.id, auth_type=invited_user.auth_type)
            user_api_client.add_user_to_service(invited_user.service,
                                                existing_user.id,
                                                invited_user.permissions,
                                                invited_user.folder_permissions)
            return redirect(url_for('main.service_dashboard', service_id=invited_user.service))
    else:
        return redirect(url_for('main.register_from_invite'))


@main.route("/organisation-invitation/<token>")
def accept_org_invite(token):
    invited_org_user = org_invite_api_client.check_token(token)
    if not current_user.is_anonymous and current_user.email_address.lower() != invited_org_user.email_address.lower():
        message = Markup("""
            You’re signed in as {}.
            This invite is for another email address.
            <a href={}>Sign out</a> and click the link again to accept this invite.
            """.format(
            current_user.email_address,
            url_for("main.sign_out", _external=True)))

        flash(message=message)

        abort(403)

    if invited_org_user.status == 'cancelled':
        invited_by = user_api_client.get_user(invited_org_user.invited_by)
        organisation = organisations_client.get_organisation(invited_org_user.organisation)
        return render_template('views/cancelled-invitation.html',
                               from_user=invited_by.name,
                               organisation_name=organisation['name'])

    if invited_org_user.status == 'accepted':
        session.pop('invited_org_user', None)
        return redirect(url_for('main.organisation_dashboard', org_id=invited_org_user.organisation))

    session['invited_org_user'] = invited_org_user.serialize()

    existing_user = user_api_client.get_user_by_email_or_none(invited_org_user.email_address)
    organisation_users = user_api_client.get_users_for_organisation(invited_org_user.organisation)

    if existing_user:
        org_invite_api_client.accept_invite(invited_org_user.organisation, invited_org_user.id)
        if existing_user not in organisation_users:
            user_api_client.add_user_to_organisation(invited_org_user.organisation, existing_user.id)
        return redirect(url_for('main.organisation_dashboard', org_id=invited_org_user.organisation))
    else:
        return redirect(url_for('main.register_from_org_invite'))

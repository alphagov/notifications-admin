from datetime import datetime, timedelta

from flask import abort, redirect, render_template, session, url_for
from flask_login import current_user

from app import invite_api_client, org_invite_api_client, user_api_client
from app.main import main
from app.main.forms import (
    RegisterUserForm,
    RegisterUserFromInviteForm,
    RegisterUserFromOrgInviteForm,
)
from app.main.views.verify import activate_user


@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user and current_user.is_authenticated:
        return redirect(url_for('main.show_accounts_or_dashboard'))

    form = RegisterUserForm()
    if form.validate_on_submit():
        _do_registration(form, send_sms=False)
        return redirect(url_for('main.registration_continue'))

    return render_template('views/register.html', form=form)


@main.route('/register-from-invite', methods=['GET', 'POST'])
def register_from_invite():
    invited_user = session.get('invited_user')
    if not invited_user:
        abort(404)

    is_sms_auth = invited_user['auth_type'] == 'sms_auth'

    form = RegisterUserFromInviteForm(invited_user)

    if form.validate_on_submit():
        if form.service.data != invited_user['service'] or form.email_address.data != invited_user['email_address']:
            abort(400)
        _do_registration(form, send_email=False, send_sms=is_sms_auth)
        invite_api_client.accept_invite(invited_user['service'], invited_user['id'])
        if is_sms_auth:
            return redirect(url_for('main.verify'))
        else:
            # we've already proven this user has email because they clicked the invite link,
            # so just activate them straight away
            return activate_user(session['user_details']['id'])

    return render_template('views/register-from-invite.html', invited_user=invited_user, form=form)


@main.route('/register-from-org-invite', methods=['GET', 'POST'])
def register_from_org_invite():
    invited_org_user = session.get('invited_org_user')
    if not invited_org_user:
        abort(404)

    form = RegisterUserFromOrgInviteForm(
        invited_org_user,
    )
    form.auth_type.data = 'sms_auth'

    if form.validate_on_submit():
        if (form.organisation.data != invited_org_user['organisation'] or
                form.email_address.data != invited_org_user['email_address']):
            abort(400)
        _do_registration(form, send_email=False, send_sms=True, organisation_id=invited_org_user['organisation'])
        org_invite_api_client.accept_invite(invited_org_user['organisation'], invited_org_user['id'])
        user_api_client.add_user_to_organisation(invited_org_user['organisation'], session['user_details']['id'])

        return redirect(url_for('main.verify'))
    return render_template('views/register-from-org-invite.html', invited_org_user=invited_org_user, form=form)


def _do_registration(form, send_sms=True, send_email=True, organisation_id=None):
    if user_api_client.is_email_already_in_use(form.email_address.data):
        user = user_api_client.get_user_by_email(form.email_address.data)
        if send_email:
            user_api_client.send_already_registered_email(user.id, user.email_address)
        session['expiry_date'] = str(datetime.utcnow() + timedelta(hours=1))
        session['user_details'] = {"email": user.email_address, "id": user.id}
    else:
        user = user_api_client.register_user(form.name.data,
                                             form.email_address.data,
                                             form.mobile_number.data or None,
                                             form.password.data,
                                             form.auth_type.data)
        if send_email:
            user_api_client.send_verify_email(user.id, user.email_address)

        if send_sms:
            user_api_client.send_verify_code(user.id, 'sms', user.mobile_number)
        session['expiry_date'] = str(datetime.utcnow() + timedelta(hours=1))
        session['user_details'] = {"email": user.email_address, "id": user.id}
    if organisation_id:
        session['organisation_id'] = organisation_id


@main.route('/registration-continue')
def registration_continue():
    if not session.get('user_details'):
        return redirect(url_for('.show_accounts_or_dashboard'))
    return render_template('views/registration-continue.html')

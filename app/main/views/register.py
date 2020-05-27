from datetime import datetime, timedelta

from flask import abort, redirect, render_template, session, url_for
from flask_login import current_user

from app.main import main
from app.main.forms import (
    RegisterUserForm,
    RegisterUserFromInviteForm,
    RegisterUserFromOrgInviteForm,
)
from app.main.views.verify import activate_user
from app.models.user import InvitedOrgUser, InvitedUser, User
from app.utils import hide_from_search_engines


@main.route('/register', methods=['GET', 'POST'])
@hide_from_search_engines
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
    invited_user = InvitedUser.from_session()
    if not invited_user:
        abort(404)

    form = RegisterUserFromInviteForm(invited_user)

    if form.validate_on_submit():
        if form.service.data != invited_user.service or form.email_address.data != invited_user.email_address:
            abort(400)
        _do_registration(form, send_email=False, send_sms=invited_user.sms_auth)
        invited_user.accept_invite()
        if invited_user.sms_auth:
            return redirect(url_for('main.verify'))
        else:
            # we've already proven this user has email because they clicked the invite link,
            # so just activate them straight away
            return activate_user(session['user_details']['id'])

    return render_template('views/register-from-invite.html', invited_user=invited_user, form=form)


@main.route('/register-from-org-invite', methods=['GET', 'POST'])
def register_from_org_invite():
    invited_org_user = InvitedOrgUser.from_session()
    if not invited_org_user:
        abort(404)

    form = RegisterUserFromOrgInviteForm(
        invited_org_user,
    )
    form.auth_type.data = 'sms_auth'

    if form.validate_on_submit():
        if (form.organisation.data != invited_org_user.organisation or
                form.email_address.data != invited_org_user.email_address):
            abort(400)
        _do_registration(form, send_email=False, send_sms=True, organisation_id=invited_org_user.organisation)
        invited_org_user.accept_invite()

        return redirect(url_for('main.verify'))
    return render_template('views/register-from-org-invite.html', invited_org_user=invited_org_user, form=form)


def _do_registration(form, send_sms=True, send_email=True, organisation_id=None):
    user = User.from_email_address_or_none(form.email_address.data)
    if user:
        if send_email:
            user.send_already_registered_email()
        session['expiry_date'] = str(datetime.utcnow() + timedelta(hours=1))
        session['user_details'] = {"email": user.email_address, "id": user.id}
    else:
        user = User.register(
            name=form.name.data,
            email_address=form.email_address.data,
            mobile_number=form.mobile_number.data,
            password=form.password.data,
            auth_type=form.auth_type.data,
        )

        if send_email:
            user.send_verify_email()

        if send_sms:
            user.send_verify_code()
        session['expiry_date'] = str(datetime.utcnow() + timedelta(hours=1))
        session['user_details'] = {"email": user.email_address, "id": user.id}
    if organisation_id:
        session['organisation_id'] = organisation_id


@main.route('/registration-continue')
def registration_continue():
    if not session.get('user_details'):
        return redirect(url_for('.show_accounts_or_dashboard'))
    return render_template('views/registration-continue.html')

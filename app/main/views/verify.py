import json

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    session,
    url_for,
)
from itsdangerous import SignatureExpired
from notifications_utils.url_safe_token import check_token

from app import user_api_client
from app.main import main
from app.main.forms import TwoFactorForm
from app.models.user import InvitedUser, User
from app.utils import redirect_to_sign_in


@main.route('/verify', methods=['GET', 'POST'])
@redirect_to_sign_in
def verify():
    user_id = session['user_details']['id']

    def _check_code(code):
        return user_api_client.check_verify_code(user_id, code, 'sms')

    form = TwoFactorForm(_check_code)

    if form.validate_on_submit():
        try:
            return activate_user(user_id)
        finally:
            session.pop('user_details', None)

    return render_template('views/two-factor.html', form=form)


@main.route('/verify-email/<token>')
def verify_email(token):
    try:
        token_data = check_token(
            token,
            current_app.config['SECRET_KEY'],
            current_app.config['DANGEROUS_SALT'],
            current_app.config['EMAIL_EXPIRY_SECONDS']
        )
    except SignatureExpired:
        flash("The link in the email we sent you has expired. We've sent you a new one.")
        return redirect(url_for('main.resend_email_verification'))

    # token contains json blob of format: {'user_id': '...', 'secret_code': '...'} (secret_code is unused)
    token_data = json.loads(token_data)
    user = User.from_id(token_data['user_id'])
    if not user:
        abort(404)

    if user.is_active:
        flash("That verification link has expired.")
        return redirect(url_for('main.sign_in'))

    session['user_details'] = {"email": user.email_address, "id": user.id}
    user.send_verify_code()
    return redirect(url_for('main.verify'))


def activate_user(user_id):
    user = User.from_id(user_id)
    # the user will have a new current_session_id set by the API - store it in the cookie for future requests
    session['current_session_id'] = user.current_session_id
    organisation_id = session.get('organisation_id')
    activated_user = user.activate()
    activated_user.login()

    invited_user = session.get('invited_user')
    if invited_user:
        service_id = _add_invited_user_to_service(invited_user)
        return redirect(url_for('main.service_dashboard', service_id=service_id))

    invited_org_user = session.get('invited_org_user')
    if invited_org_user:
        user_api_client.add_user_to_organisation(invited_org_user['organisation'], session['user_details']['id'])

    if organisation_id:
        return redirect(url_for('main.organisation_dashboard', org_id=organisation_id))
    else:
        return redirect(url_for('main.add_service', first='first'))


def _add_invited_user_to_service(invited_user):
    invitation = InvitedUser(**invited_user)
    user = User.from_id(session['user_id'])
    service_id = invited_user['service']
    user_api_client.add_user_to_service(service_id, user.id, invitation.permissions, invitation.folder_permissions)
    return service_id

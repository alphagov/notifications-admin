import json

from flask import (
    render_template,
    redirect,
    session,
    url_for,
    current_app,
    flash,
    abort
)

from itsdangerous import SignatureExpired

from flask_login import login_user

from notifications_utils.url_safe_token import check_token

from app.main import main
from app.main.forms import TwoFactorForm
from app.utils import redirect_to_sign_in

from app import user_api_client


@main.route('/verify', methods=['GET', 'POST'])
@redirect_to_sign_in
def verify():
    user_id = session['user_details']['id']

    def _check_code(code):
        return user_api_client.check_verify_code(user_id, code, 'sms')

    form = TwoFactorForm(_check_code)

    if form.validate_on_submit():
        try:
            user = user_api_client.get_user(user_id)
            # the user will have a new current_session_id set by the API - store it in the cookie for future requests
            session['current_session_id'] = user.current_session_id
            activated_user = user_api_client.activate_user(user)
            login_user(activated_user)
            return redirect(url_for('main.add_service', first='first'))
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
    user = user_api_client.get_user(token_data['user_id'])
    if not user:
        abort(404)

    if user.is_active:
        flash("That verification link has expired.")
        return redirect(url_for('main.sign_in'))

    session['user_details'] = {"email": user.email_address, "id": user.id}
    user_api_client.send_verify_code(user.id, 'sms', user.mobile_number)
    return redirect('verify')

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

from notifications_python_client.errors import HTTPError

from app.main import main
from app.main.forms import TwoFactorForm

from app import user_api_client


@main.route('/verify', methods=['GET', 'POST'])
def verify():
    # TODO there needs to be a way to regenerate a session id
    # or handle gracefully.
    user_id = session['user_details']['id']

    def _check_code(code):
        return user_api_client.check_verify_code(user_id, code, 'sms')

    form = TwoFactorForm(_check_code)

    if form.validate_on_submit():
        try:
            user = user_api_client.get_user(user_id)
            activated_user = user_api_client.activate_user(user)
            login_user(activated_user)
            return redirect(url_for('main.add_service', first='first'))
        finally:
            session.pop('user_details', None)

    return render_template('views/two-factor.html', form=form)


@main.route('/verify-email/<token>')
def verify_email(token):
    from utils.url_safe_token import check_token
    try:
        token_data = check_token(token,
                                 current_app.config['SECRET_KEY'],
                                 current_app.config['DANGEROUS_SALT'],
                                 current_app.config['EMAIL_EXPIRY_SECONDS'])

        token_data = json.loads(token_data)
        verified = user_api_client.check_verify_code(token_data['user_id'], token_data['secret_code'], 'email')
        user = user_api_client.get_user(token_data['user_id'])
        if not user:
            abort(404)

        if user.is_active():
            flash("You have already verified your email address.")
            return redirect(url_for('main.sign_in'))

        session['user_details'] = {"email": user.email_address, "id": user.id}
        if verified[0]:
            user_api_client.send_verify_code(user.id, 'sms', user.mobile_number)
            return redirect('verify')
        else:
            if verified[1] == 'Code has expired':
                flash("The link in the email we sent you has expired. We've sent you a new one.")
                return redirect(url_for('main.resend_email_verification'))
            else:
                message = "There was a problem verifying your account. Error message: '{}'".format(verified[1])
                flash(message)
                return redirect(url_for('main.index'))

    except SignatureExpired:
        flash('The link in the email we sent you has expired')
        return redirect(url_for('main.resend_email_verification'))

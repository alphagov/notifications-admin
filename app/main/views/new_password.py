import json

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from itsdangerous import SignatureExpired
from notifications_utils.url_safe_token import check_token

from app.main import main
from app.main.forms import NewPasswordForm
from app.models.user import User
from app.utils.login import log_in_user


@main.route('/new-password/<path:token>', methods=['GET', 'POST'])
def new_password(token):
    try:
        token_data = check_token(token, current_app.config['SECRET_KEY'], current_app.config['DANGEROUS_SALT'],
                                 current_app.config['EMAIL_EXPIRY_SECONDS'])
    except SignatureExpired:
        flash('The link in the email we sent you has expired. Enter your email address to resend.')
        return redirect(url_for('.forgot_password'))

    email_address = json.loads(token_data)['email']
    user = User.from_email_address(email_address)
    if user.password_changed_more_recently_than(json.loads(token_data)['created_at']):
        flash('The link in the email has already been used')
        return redirect(url_for('main.index'))

    if request.method == 'GET':
        user.update_email_access_validated_at()

    form = NewPasswordForm()

    if form.validate_on_submit():
        user.reset_failed_login_count()
        session['user_details'] = {
            'id': user.id,
            'email': user.email_address,
            'password': form.new_password.data}
        if user.email_auth:
            # they've just clicked an email link, so have done an email auth journey anyway. Just log them in.
            return log_in_user(user.id)
        elif user.webauthn_auth:
            return redirect(url_for('main.two_factor_webauthn', next=request.args.get('next')))
        else:
            # send user a 2fa sms code
            user.send_verify_code()
            return redirect(url_for('main.two_factor_sms', next=request.args.get('next')))
    else:
        return render_template('views/new-password.html', token=token, form=form, user=user)

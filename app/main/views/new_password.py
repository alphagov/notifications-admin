import json

from flask import (render_template, url_for, redirect, flash, session, current_app, abort)
from itsdangerous import SignatureExpired

from app.main import main
from app.main.forms import NewPasswordForm
from datetime import datetime
from app import user_api_client


@main.route('/new-password/<path:token>', methods=['GET', 'POST'])
def new_password(token):
    from notifications_utils.url_safe_token import check_token
    try:
        token_data = check_token(token, current_app.config['SECRET_KEY'], current_app.config['DANGEROUS_SALT'],
                                 current_app.config['TOKEN_MAX_AGE_SECONDS'])
    except SignatureExpired:
        flash('The link in the email we sent you has expired. Enter your email address to resend.')
        return redirect(url_for('.forgot_password'))

    email_address = json.loads(token_data)['email']
    user = user_api_client.get_user_by_email(email_address)
    if user.password_changed_at and datetime.strptime(user.password_changed_at, '%Y-%m-%d %H:%M:%S.%f') > \
            datetime.strptime(json.loads(token_data)['created_at'], '%Y-%m-%d %H:%M:%S.%f'):
        flash('The link in the email has already been used')
        return redirect(url_for('main.index'))

    form = NewPasswordForm()

    if form.validate_on_submit():
        user_api_client.send_verify_code(user.id, 'sms', user.mobile_number)
        session['user_details'] = {
            'id': user.id,
            'email': user.email_address,
            'password': form.new_password.data}
        return redirect(url_for('main.two_factor'))
    else:
        return render_template('views/new-password.html', token=token, form=form, user=user)

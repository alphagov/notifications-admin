from flask import (render_template, url_for, redirect, flash, session)

from app.main import main
from app.main.dao import users_dao
from app.main.forms import NewPasswordForm
from app.notify_client.sender import check_token


@main.route('/new-password/<path:token>', methods=['GET', 'POST'])
def new_password(token):
    email_address = check_token(token)
    if not email_address:
        flash('The link in the email we sent you has expired. Enter your email address to resend.')
        return redirect(url_for('.forgot_password'))

    user = users_dao.get_user_by_email(email_address=email_address)
    if user and user.state != 'request_password_reset':
        flash('The link in the email we sent you has already been used.')
        return redirect(url_for('.index'))

    form = NewPasswordForm()

    if form.validate_on_submit():
        users_dao.send_verify_code(user.id, 'sms')
        session['user_details'] = {
            'id': user.id,
            'email': user.email_address,
            'password': form.new_password.data}
        users_dao.activate_user(user)
        return redirect(url_for('main.two_factor'))
    else:
        return render_template('views/new-password.html', token=token, form=form, user=user)

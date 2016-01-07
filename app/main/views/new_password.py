from datetime import datetime

from flask import (render_template, url_for, redirect, flash, current_app)

from app.main import main
from app.main.dao import users_dao
from app.main.forms import NewPasswordForm
from app.main.views import send_sms_code, check_token


@main.route('/new-password/<path:token>', methods=['GET', 'POST'])
def new_password(token):
    form = NewPasswordForm()
    if form.validate_on_submit():
        email_address = check_token(token)
        if email_address:
            user = users_dao.update_password(email_address.decode('utf-8'), form.new_password.data)
            send_sms_code(user.id, user.mobile_number)
            return redirect(url_for('main.two_factor'))
        else:
            flash('expired token request again')
            current_app.logger.info('we got here')
            return redirect(url_for('.forgot_password'))
    else:
        return render_template('views/new-password.html', toke=token, form=form)


def valid_token(token):
    return token and datetime.now() <= token.expiry_date

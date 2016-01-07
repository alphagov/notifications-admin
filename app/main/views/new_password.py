from datetime import datetime

from flask import (Markup, render_template, url_for, redirect)

from app.main import main
from app.main.dao import (password_reset_token_dao, users_dao)
from app.main.forms import NewPasswordForm
from app.main.views import send_sms_code


@main.route('/new-password/<path:token>', methods=['GET', 'POST'])
def new_password(token):
    form = NewPasswordForm()
    if form.validate_on_submit():
        password_reset_token = password_reset_token_dao.get_token(str(Markup.escape(token)))
        if not valid_token(password_reset_token):
            form.new_password.errors.append('token is invalid')  # Is there a better way
            return render_template('views/new-password.html', form=form)
        else:
            users_dao.update_password(password_reset_token.user_id, form.new_password.data)
            user = users_dao.get_user_by_id(password_reset_token.user_id)
            send_sms_code(user.id, user.mobile_number)
            return redirect(url_for('main.two_factor'))
    else:
        return render_template('views/new-password.html', toke=token, form=form)


def valid_token(token):
    return token and datetime.now() <= token.expiry_date

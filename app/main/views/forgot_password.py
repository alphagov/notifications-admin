from flask import render_template

from app.main import main
from app.main.dao import users_dao
from app.main.forms import ForgotPasswordForm
from app.main.views import send_change_password_email


@main.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm(users_dao.find_all_email_address())
    if form.validate_on_submit():
        user = users_dao.get_user_by_email(form.email_address.data)
        send_change_password_email(form.email_address.data, user.id)
        return render_template('views/password-reset-sent.html')
    else:
        return render_template('views/forgot-password.html', form=form)

from flask import render_template, current_app
from app.main import main
from app.main.dao import users_dao
from app.main.forms import ForgotPasswordForm
from app.notify_client.sender import send_change_password_email


@main.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():

    def _email_exists(email):
        return not users_dao.is_email_unique(email)

    form = ForgotPasswordForm(_email_exists)
    if form.validate_on_submit():
        user = users_dao.get_user_by_email(form.email_address.data)
        users_dao.request_password_reset(user)
        send_change_password_email(form.email_address.data)
        return render_template('views/password-reset-sent.html')

    return render_template('views/forgot-password.html', form=form)

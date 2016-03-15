from flask import (
    render_template,
)

from app.main import main
from app.main.forms import ForgotPasswordForm
from app import user_api_client


@main.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user_api_client.send_reset_password_url(form.email_address.data)

        return render_template('views/password-reset-sent.html')

    return render_template('views/forgot-password.html', form=form)

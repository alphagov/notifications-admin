from flask import (
    render_template,
)
from notifications_python_client.errors import HTTPError

from app.main import main
from app.main.forms import ForgotPasswordForm
from app import user_api_client


@main.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        try:
            user_api_client.send_reset_password_url(form.email_address.data)
        except HTTPError as e:
            if e.status_code == 404:
                return render_template('views/password-reset-sent.html')
            else:
                raise e
        return render_template('views/password-reset-sent.html')

    return render_template('views/forgot-password.html', form=form)

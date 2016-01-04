from flask import render_template, jsonify

from app.main import main
from app.main.forms import ForgotPassword
from app.main.views import send_change_password_email


@main.route('/forgot-password', methods=['GET'])
def render_forgot_my_password():
    return render_template('views/forgot-password.html', form=ForgotPassword())


@main.route('/forgot-password', methods=['POST'])
def change_password():
    form = ForgotPassword()
    if form.validate_on_submit():
        send_change_password_email(form.email_address)

        return 'You have been sent an email with a link to change your password'
    else:
        return jsonify(form.errors), 400

from flask import (
    render_template, redirect, session, url_for)

from flask_login import current_user

from app.main import main
from app.main.dao import users_dao
from app.main.forms import EmailNotReceivedForm, TextNotReceivedForm


@main.route('/email-not-received', methods=['GET', 'POST'])
def check_and_resend_email_code():
    # TODO there needs to be a way to regenerate a session id
    user = users_dao.get_user_by_email(session['user_details']['email'])
    form = EmailNotReceivedForm(email_address=user.email_address)
    if form.validate_on_submit():
        users_dao.send_verify_code(user.id, 'email', to=form.email_address.data)
        user.email_address = form.email_address.data
        users_dao.update_user(user)
        return redirect(url_for('.verify'))
    return render_template('views/email-not-received.html', form=form)


@main.route('/text-not-received', methods=['GET', 'POST'])
def check_and_resend_text_code():
    # TODO there needs to be a way to regenerate a session id
    user = users_dao.get_user_by_email(session['user_details']['email'])
    form = TextNotReceivedForm(mobile_number=user.mobile_number)
    if form.validate_on_submit():
        users_dao.send_verify_code(user.id, 'sms', to=form.mobile_number.data)
        user.mobile_number = form.mobile_number.data
        users_dao.update_user(user)
        return redirect(url_for('.verify'))
    return render_template('views/text-not-received.html', form=form)


@main.route('/verification-not-received', methods=['GET'])
def verification_code_not_received():
    return render_template('views/verification-not-received.html')


@main.route('/send-new-code', methods=['GET'])
def check_and_resend_verification_code():
    # TODO there needs to be a way to generate a new session id
    user = users_dao.get_user_by_email(session['user_details']['email'])
    users_dao.send_verify_code(user.id, 'sms', user.mobile_number)
    return redirect(url_for('main.two_factor'))

from flask import (
    render_template,
    redirect,
    session,
    url_for
)

from app import user_api_client
from app.main import main
from app.main.forms import TextNotReceivedForm


@main.route('/resend-email-verification')
def resend_email_verification():
    # TODO there needs to be a way to regenerate a session id
    user = user_api_client.get_user_by_email(session['user_details']['email'])
    user_api_client.send_verify_email(user.id, user.email_address)
    return render_template('views/resend-email-verification.html', email=user.email_address)


@main.route('/text-not-received', methods=['GET', 'POST'])
def check_and_resend_text_code():
    # TODO there needs to be a way to regenerate a session id
    user = user_api_client.get_user_by_email(session['user_details']['email'])
    form = TextNotReceivedForm(mobile_number=user.mobile_number)
    if form.validate_on_submit():
        user_api_client.send_verify_code(user.id, 'sms', to=form.mobile_number.data)
        user.mobile_number = form.mobile_number.data
        user_api_client.update_user(user)
        return redirect(url_for('.verify'))
    return render_template('views/text-not-received.html', form=form)


@main.route('/verification-not-received', methods=['GET'])
def verification_code_not_received():
    return render_template('views/verification-not-received.html')


@main.route('/send-new-code', methods=['GET'])
def check_and_resend_verification_code():
    # TODO there needs to be a way to generate a new session id
    user = user_api_client.get_user_by_email(session['user_details']['email'])
    user_api_client.send_verify_code(user.id, 'sms', user.mobile_number)
    if user.state == 'pending':
        return redirect(url_for('main.verify'))
    else:
        return redirect(url_for('main.two_factor'))

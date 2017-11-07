from flask import (
    render_template,
    redirect,
    session,
    url_for
)

from app import user_api_client
from app.main import main
from app.main.forms import TextNotReceivedForm
from app.utils import redirect_to_sign_in


@main.route('/resend-email-verification')
@redirect_to_sign_in
def resend_email_verification():
    user = user_api_client.get_user_by_email(session['user_details']['email'])
    user_api_client.send_verify_email(user.id, user.email_address)
    return render_template('views/resend-email-verification.html', email=user.email_address)


@main.route('/text-not-received', methods=['GET', 'POST'])
@redirect_to_sign_in
def check_and_resend_text_code():
    user = user_api_client.get_user_by_email(session['user_details']['email'])

    if user.state == 'active':
        # this is a verified user and therefore redirect to page to request resend without edit mobile
        return render_template('views/verification-not-received.html')

    form = TextNotReceivedForm(mobile_number=user.mobile_number)
    if form.validate_on_submit():
        user_api_client.send_verify_code(user.id, 'sms', to=form.mobile_number.data)
        user = user_api_client.update_user_attribute(user.id, mobile_number=form.mobile_number.data)
        return redirect(url_for('.verify'))

    return render_template('views/text-not-received.html', form=form)


@main.route('/send-new-code', methods=['GET'])
@redirect_to_sign_in
def check_and_resend_verification_code():
    user = user_api_client.get_user_by_email(session['user_details']['email'])
    user_api_client.send_verify_code(user.id, 'sms', user.mobile_number)
    if user.state == 'pending':
        return redirect(url_for('main.verify'))
    else:
        return redirect(url_for('main.two_factor'))


@main.route('/email-not-received', methods=['GET'])
@redirect_to_sign_in
def email_not_received():
    return render_template('views/email-not-received.html')


@main.route('/send-new-email-token', methods=['GET'])
@redirect_to_sign_in
def resend_email_link():
    user_api_client.send_verify_code(session['user_details']['id'], 'email', None)
    session.pop('user_details')
    return redirect(url_for('main.two_factor_email_sent', email_resent=True))

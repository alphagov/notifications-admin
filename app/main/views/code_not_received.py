from flask import redirect, render_template, request, session, url_for

from app import user_api_client
from app.main import main
from app.main.forms import TextNotReceivedForm
from app.models.user import User
from app.utils.login import redirect_to_sign_in


@main.route('/resend-email-verification')
@redirect_to_sign_in
def resend_email_verification():
    user = User.from_email_address(session['user_details']['email'])
    user.send_verify_email()
    return render_template('views/resend-email-verification.html', email=user.email_address)


@main.route('/text-not-received', methods=['GET', 'POST'])
@redirect_to_sign_in
def check_and_resend_text_code():
    user = User.from_email_address(session['user_details']['email'])
    redirect_url = request.args.get('next')

    if user.state == 'active':
        # this is a verified user and therefore redirect to page to request resend without edit mobile
        return render_template('views/verification-not-received.html', redirect_url=redirect_url)

    form = TextNotReceivedForm(mobile_number=user.mobile_number)
    if form.validate_on_submit():
        user.send_verify_code(to=form.mobile_number.data)
        user.update(mobile_number=form.mobile_number.data)
        return redirect(url_for('.verify', next=redirect_url))

    return render_template('views/text-not-received.html', form=form)


@main.route('/send-new-code', methods=['GET'])
@redirect_to_sign_in
def check_and_resend_verification_code():
    user = User.from_email_address(session['user_details']['email'])
    user.send_verify_code()
    redirect_url = request.args.get('next')
    if user.state == 'pending':
        return redirect(url_for('main.verify', next=redirect_url))
    else:
        return redirect(url_for('main.two_factor_sms', next=redirect_url))


@main.route('/email-not-received', methods=['GET'])
@redirect_to_sign_in
def email_not_received():
    redirect_url = request.args.get('next')
    return render_template('views/email-not-received.html', redirect_url=redirect_url)


@main.route('/send-new-email-token', methods=['GET'])
@redirect_to_sign_in
def resend_email_link():
    user_api_client.send_verify_code(session['user_details']['id'], 'email', None)
    session.pop('user_details')
    return redirect(url_for('main.two_factor_email_sent', email_resent=True))

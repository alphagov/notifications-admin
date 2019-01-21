import json

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_user
from itsdangerous import SignatureExpired
from notifications_utils.url_safe_token import check_token

from app import user_api_client
from app.main import main
from app.main.forms import TwoFactorForm
from app.utils import redirect_to_sign_in


@main.route('/two-factor-email-sent', methods=['GET'])
def two_factor_email_sent():
    title = 'Email resent' if request.args.get('email_resent') else 'Check your email'
    return render_template(
        'views/two-factor-email.html',
        title=title
    )


@main.route('/email-auth/<token>', methods=['GET'])
def two_factor_email(token):
    if current_user.is_authenticated:
        return redirect_when_logged_in(current_user.id)

    # checks url is valid, and hasn't timed out
    try:
        token_data = json.loads(check_token(
            token,
            current_app.config['SECRET_KEY'],
            current_app.config['DANGEROUS_SALT'],
            current_app.config['EMAIL_2FA_EXPIRY_SECONDS']
        ))
    except SignatureExpired:
        # lets decode again, without the expiry, to get the user id out
        orig_data = json.loads(check_token(
            token,
            current_app.config['SECRET_KEY'],
            current_app.config['DANGEROUS_SALT'],
            None
        ))
        session['user_details'] = {'id': orig_data['user_id']}
        flash("The link in the email we sent you has expired. We’ve sent you a new one.")
        return redirect(url_for('.resend_email_link'))

    user_id = token_data['user_id']
    # checks if code was already used
    logged_in, msg = user_api_client.check_verify_code(user_id, token_data['secret_code'], "email")

    if not logged_in:
        flash("This link has already been used")
        session['user_details'] = {'id': user_id}
        return redirect(url_for('.resend_email_link'))
    return log_in_user(user_id)


@main.route('/two-factor', methods=['GET', 'POST'])
@redirect_to_sign_in
def two_factor():
    user_id = session['user_details']['id']

    def _check_code(code):
        return user_api_client.check_verify_code(user_id, code, "sms")

    form = TwoFactorForm(_check_code)

    if form.validate_on_submit():
        return log_in_user(user_id)

    return render_template('views/two-factor.html', form=form)


# see http://flask.pocoo.org/snippets/62/
def _is_safe_redirect_url(target):
    from urllib.parse import urlparse, urljoin
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in ('http', 'https') and \
        host_url.netloc == redirect_url.netloc


def log_in_user(user_id):
    try:
        user = user_api_client.get_user(user_id)
        # the user will have a new current_session_id set by the API - store it in the cookie for future requests
        session['current_session_id'] = user.current_session_id
        # Check if coming from new password page
        if 'password' in session.get('user_details', {}):
            user = user_api_client.update_password(user.id, password=session['user_details']['password'])
        activated_user = user_api_client.activate_user(user)
        login_user(activated_user)
    finally:
        # get rid of anything in the session that we don't expect to have been set during register/sign in flow
        session.pop("user_details", None)
        session.pop("file_uploads", None)

    return redirect_when_logged_in(user_id)


def redirect_when_logged_in(user_id):
    next_url = request.args.get('next')
    if next_url and _is_safe_redirect_url(next_url):
        return redirect(next_url)
    if current_user.platform_admin:
        return redirect(url_for('main.platform_admin'))

    return redirect(url_for('main.show_accounts_or_dashboard'))

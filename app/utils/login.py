from functools import wraps

from flask import redirect, request, session, url_for

from app.models.user import User
from app.utils.time import is_less_than_days_ago


def redirect_to_sign_in(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'user_details' not in session:
            return redirect(url_for('main.sign_in'))
        else:
            return f(*args, **kwargs)
    return wrapped


def log_in_user(user_id):
    try:
        user = User.from_id(user_id)
        # the user will have a new current_session_id set by the API - store it in the cookie for future requests
        session['current_session_id'] = user.current_session_id
        # Check if coming from new password page
        if 'password' in session.get('user_details', {}):
            user.update_password(session['user_details']['password'])
        user.activate()
        user.login()
    finally:
        # get rid of anything in the session that we don't expect to have been set during register/sign in flow
        session.pop("user_details", None)
        session.pop("file_uploads", None)

    return redirect_when_logged_in(platform_admin=user.platform_admin)


def redirect_when_logged_in(platform_admin):
    next_url = request.args.get('next')
    if next_url and is_safe_redirect_url(next_url):
        return redirect(next_url)

    return redirect(url_for('main.show_accounts_or_dashboard'))


def email_needs_revalidating(user):
    return not is_less_than_days_ago(user.email_access_validated_at, 90)


# see https://stackoverflow.com/questions/60532973/how-do-i-get-a-is-safe-url-function-to-use-with-flask-and-how-does-it-work  # noqa
def is_safe_redirect_url(target):
    from urllib.parse import urljoin, urlparse
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in ('http', 'https') and \
        host_url.netloc == redirect_url.netloc

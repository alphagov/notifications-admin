from functools import wraps

from flask import abort, current_app
from flask_login import current_user, login_required
from notifications_utils.user import GOVERNMENT_EMAIL_DOMAIN_NAMES, email_address_ends_with

from app.notify_client.organisations_api_client import organisations_client

user_is_logged_in = login_required


def user_has_permissions(*permissions, **permission_kwargs):
    def wrap(func):
        @wraps(func)
        def wrap_func(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()
            if not current_user.has_permissions(*permissions, **permission_kwargs):
                abort(403)
            return func(*args, **kwargs)

        return wrap_func

    return wrap


def user_is_gov_user(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        if not current_user.is_gov_user:
            abort(403)
        return f(*args, **kwargs)

    return wrapped


def user_is_platform_admin(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        if not current_user.platform_admin:
            abort(403)
        return f(*args, **kwargs)

    return wrapped


def is_gov_user(email_address):
    return email_address_ends_with(email_address, GOVERNMENT_EMAIL_DOMAIN_NAMES) or email_address_ends_with(
        email_address, organisations_client.get_domains()
    )

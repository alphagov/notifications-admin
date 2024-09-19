import os
from datetime import datetime
from functools import wraps

import pytz
from flask import abort, current_app
from flask_login import current_user, login_required

from app.notify_client.organisations_api_client import organisations_client

user_is_logged_in = login_required


with open(f"{os.path.dirname(os.path.realpath(__file__))}/email_domains.txt") as email_domains:
    GOVERNMENT_EMAIL_DOMAIN_NAMES = [line.strip() for line in email_domains]


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
    return _email_address_ends_with(email_address, GOVERNMENT_EMAIL_DOMAIN_NAMES) or _email_address_ends_with(
        email_address, organisations_client.get_domains()
    )


def _email_address_ends_with(email_address, known_domains):
    return any(
        email_address.lower().endswith(
            (
                f"@{known}",
                f".{known}",
            )
        )
        for known in known_domains
    )


def normalise_email_address_aliases(email_address):
    local_part, domain = email_address.split("@")
    local_part = local_part.split("+")[0].replace(".", "")

    return f"{local_part}@{domain}".lower()


def get_user_created_at_for_ticket(user) -> datetime | None:
    if user.is_authenticated:
        return datetime.strptime(user.created_at, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.utc)

    return None

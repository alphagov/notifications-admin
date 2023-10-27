from flask import Blueprint, request, session

from app.utils.constants import JSON_UPDATES_BLUEPRINT_NAME

main = Blueprint("main", __name__)
json_updates = Blueprint(JSON_UPDATES_BLUEPRINT_NAME, __name__)
no_cookie = Blueprint("no_cookie", __name__)

from app.main.views import (  # noqa
    add_service,
    agreement,
    api_keys,
    broadcast,
    choose_account,
    code_not_received,
    conversation,
    dashboard,
    email_branding,
    feedback,
    find_users,
    forgot_password,
    history,
    inbound_number,
    index,
    invites,
    jobs,
    letter_branding,
    make_service_live,
    manage_users,
    new_password,
    notifications,
    performance,
    platform_admin,
    pricing,
    providers,
    register,
    returned_letters,
    security_policy,
    send,
    sign_in,
    sign_out,
    templates,
    tour,
    two_factor,
    uploads,
    user_profile,
    verify,
    webauthn_credentials,
)
from app.main.views.organisations import branding, index  # noqa
from app.main.views.service_settings import branding, index  # noqa


def make_session_permanent():
    """
    Make sessions permanent. By permanent, we mean "admin app sets when it expires". Normally the cookie would expire
    whenever you close the browser. With this, the session expiry is set in `config['PERMANENT_SESSION_LIFETIME']`
    (20 hours) and is refreshed after every request. IE: you will be logged out after twenty hours of inactivity.

    We don't _need_ to set this every request (it's saved within the cookie itself under the `_permanent` flag), only
    when you first log in/sign up/get invited/etc, but we do it just to be safe. For more reading, check here:
    https://stackoverflow.com/questions/34118093/flask-permanent-session-where-to-define-them
    """
    session.permanent = True


def save_service_or_org_after_request(response):
    # Only save the current session if the request is 200
    service_id = request.view_args.get("service_id", None) if request.view_args else None
    organisation_id = request.view_args.get("org_id", None) if request.view_args else None
    if response.status_code == 200:
        if service_id:
            session["service_id"] = service_id
            session["organisation_id"] = None
        elif organisation_id:
            session["service_id"] = None
            session["organisation_id"] = organisation_id
    return response


main.before_request(make_session_permanent)
main.after_request(save_service_or_org_after_request)

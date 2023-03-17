from flask import Blueprint

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
    find_services,
    find_users,
    forgot_password,
    history,
    inbound_number,
    index,
    invites,
    jobs,
    join_service,
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

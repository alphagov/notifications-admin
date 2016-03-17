from flask import Blueprint

main = Blueprint('main', __name__)

from app.main.views import (
    index,
    sign_in,
    sign_out,
    register,
    two_factor,
    verify,
    send,
    add_service,
    code_not_received,
    jobs, dashboard,
    templates,
    service_settings,
    forgot_password,
    new_password,
    styleguide,
    user_profile,
    choose_service,
    api_keys,
    manage_users,
    invites,
    all_services
)

from flask import Blueprint

main = Blueprint('main', __name__)  # noqa

from app.main.views import (  # noqa
    index,
    sign_in,
    sign_out,
    register,
    two_factor,
    verify,
    send,
    add_service,
    code_not_received,
    jobs,
    dashboard,
    templates,
    service_settings,
    forgot_password,
    new_password,
    styleguide,
    user_profile,
    choose_account,
    api_keys,
    manage_users,
    invites,
    feedback,
    providers,
    platform_admin,
    letter_jobs,
    email_branding,
    conversation,
    organisations,
    notifications,
    inbound_number,
    agreement,
    document_download
)

from flask import request

from app.notify_client.events_api_client import events_api_client

EVENT_SCHEMAS = {
    "sucessful_login": {"user_id"},
    "update_user_email": {"user_id", "updated_by_id", "original_email_address", "new_email_address"},
    "update_user_mobile_number": {"user_id", "updated_by_id", "original_mobile_number", "new_mobile_number"},
    "remove_user_from_service": {"user_id", "removed_by_id", "service_id"},
    "add_user_to_service": {"user_id", "invited_by_id", "service_id", "ui_permissions"},
    "set_user_permissions": {"user_id", "service_id", "original_ui_permissions", "new_ui_permissions", "set_by_id"},
    "archive_user": {"user_id", "user_email_address", "archived_by_id"},
    "change_broadcast_account_type": {
        "service_id",
        "changed_by_id",
        "service_mode",
        "broadcast_channel",
        "provider_restriction",
    },
    "archive_service": {"service_id", "archived_by_id"},
    "update_email_branding": {"email_branding_id", "updated_by_id", "old_email_branding"},
    "update_letter_branding": {"letter_branding_id", "updated_by_id", "old_letter_branding"},
    "set_inbound_sms_on": {"user_id", "service_id", "inbound_number_id"},
}


def on_user_logged_in(_sender, user):
    _send_event("sucessful_login", user_id=user.id)


def create_email_change_event(**kwargs):
    _send_event("update_user_email", **kwargs)


def create_mobile_number_change_event(**kwargs):
    _send_event("update_user_mobile_number", **kwargs)


def create_remove_user_from_service_event(**kwargs):
    _send_event("remove_user_from_service", **kwargs)


def create_add_user_to_service_event(**kwargs):
    _send_event("add_user_to_service", **kwargs)


def create_set_user_permissions_event(**kwargs):
    _send_event("set_user_permissions", **kwargs)


def create_archive_user_event(**kwargs):
    _send_event("archive_user", **kwargs)


def create_broadcast_account_type_change_event(**kwargs):
    _send_event("change_broadcast_account_type", **kwargs)


def create_archive_service_event(**kwargs):
    _send_event("archive_service", **kwargs)


def create_update_email_branding_event(**kwargs):
    _send_event("update_email_branding", **kwargs)


def create_update_letter_branding_event(**kwargs):
    _send_event("update_letter_branding", **kwargs)


def create_set_inbound_sms_on_event(**kwargs):
    _send_event("set_inbound_sms_on", **kwargs)


def _send_event(event_type, **kwargs):
    expected_keys = EVENT_SCHEMAS[event_type]
    actual_keys = set(kwargs.keys())

    if expected_keys != actual_keys:
        raise ValueError(f"Expected {expected_keys}, but got {actual_keys}")

    event_data = _construct_event_data(request)
    event_data.update(kwargs)

    events_api_client.create_event(event_type, event_data)


def _construct_event_data(request):
    return {"ip_address": _get_remote_addr(request), "browser_fingerprint": _get_browser_fingerprint(request)}


# This might not be totally correct depending on proxy setup
def _get_remote_addr(request):
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0]
    else:
        return request.remote_addr


def _get_browser_fingerprint(request):
    browser = request.user_agent.browser
    version = request.user_agent.version
    platform = request.user_agent.platform
    user_agent_string = request.user_agent.string
    # at some point this may be hashed?
    finger_print = {
        "browser": browser,
        "platform": platform,
        "version": version,
        "user_agent_string": user_agent_string,
    }

    return finger_print

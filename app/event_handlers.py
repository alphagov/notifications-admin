import inspect
from flask import request

from app.notify_client.events_api_client import events_api_client


class Event:
    def __init__(self, name, schema):
        self.name = name
        self.schema = schema
    def __call__(self, **kwargs):
        _send_event(self.name, self.schema, **kwargs)

class Events:

    def __new__(cls):
        for key, value in vars(cls).items():
            if key.startswith("__"):
                continue
            setattr(cls, key, Event(key, value))
        return cls

    sucessful_login = {"user_id"}
    update_user_email = {"user_id", "updated_by_id", "original_email_address", "new_email_address"}
    update_user_mobile_number = {"user_id", "updated_by_id", "original_mobile_number", "new_mobile_number"}
    remove_user_from_service = {"user_id", "removed_by_id", "service_id"}
    add_user_to_service = {"user_id", "invited_by_id", "service_id", "ui_permissions"}
    set_user_permissions = {"user_id", "service_id", "original_ui_permissions", "new_ui_permissions", "set_by_id"}
    set_organisation_user_permissions = {
        "user_id",
        "organisation_id",
        "original_permissions",
        "new_permissions",
        "set_by_id",
    }
    archive_user = {"user_id", "user_email_address", "archived_by_id"}
    archive_service = {"service_id", "archived_by_id"}
    update_email_branding = {"email_branding_id", "updated_by_id", "old_email_branding"}
    update_letter_branding = {"letter_branding_id", "updated_by_id", "old_letter_branding"}
    set_inbound_sms_on = {"user_id", "service_id", "inbound_number_id"}


events = Events()

def on_user_logged_in(_sender, user):
    events.sucessful_login(user_id=user.id)


def create_email_change_event(**kwargs):
    events.update_user_email(**kwargs)


def create_mobile_number_change_event(**kwargs):
    events.update_user_mobile_number(**kwargs)


def create_remove_user_from_service_event(**kwargs):
    events.remove_user_from_service(**kwargs)


def create_add_user_to_service_event(**kwargs):
    events.add_user_to_service(**kwargs)


def create_set_user_permissions_event(**kwargs):
    events.set_user_permissions(**kwargs)


def create_set_organisation_user_permissions_event(**kwargs):
    events.set_organisation_user_permissions(**kwargs)


def create_archive_user_event(**kwargs):
    events.archive_user(**kwargs)


def create_archive_service_event(**kwargs):
    events.archive_service(**kwargs)


def create_update_email_branding_event(**kwargs):
    events.update_email_branding(**kwargs)


def create_update_letter_branding_event(**kwargs):
    events.update_letter_branding(**kwargs)


def create_set_inbound_sms_on_event(**kwargs):
    events.set_inbound_sms_on(**kwargs)


def _send_event(event_type, schema=None, **kwargs):
    expected_keys = schema
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

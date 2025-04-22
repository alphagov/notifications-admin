from flask import request

from app.notify_client.events_api_client import events_api_client


class Event:
    def __init__(self, name, schema):
        self.name = name
        self.schema = schema

    def __call__(self, **kwargs):
        actual_keys = set(kwargs.keys())

        if self.schema != actual_keys:
            raise ValueError(f"Expected {self.schema}, but got {actual_keys}")

        event_data = _construct_event_data()
        event_data.update(kwargs)

        events_api_client.create_event(self.name, event_data)


class EventsMeta(type):
    def __init__(cls, name, bases, dict_):
        for key, value in dict_.items():
            if not key.startswith("__"):
                setattr(cls, key, Event(key, value))
        super().__init__(name, bases, dict_)


class Events(metaclass=EventsMeta):
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
    remove_platform_admin = {"user_id", "removed_by_id"}


def _construct_event_data():
    return {"ip_address": _get_remote_addr(), "browser_fingerprint": _get_browser_fingerprint()}


# This might not be totally correct depending on proxy setup
def _get_remote_addr():
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0]
    else:
        return request.remote_addr


def _get_browser_fingerprint():
    # at some point this may be hashed?
    return {
        "browser": request.user_agent.browser,
        "platform": request.user_agent.platform,
        "version": request.user_agent.version,
        "user_agent_string": request.user_agent.string,
    }

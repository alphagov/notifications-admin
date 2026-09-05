from collections.abc import Callable
from functools import wraps
from inspect import signature
from typing import cast

from flask import request

from app.notify_client.events_api_client import events_api_client


def event_creator[T: Callable](fn: T) -> T:
    sig = signature(fn)

    @wraps(fn)  # technically we don't actually wrap it, we just borrow its name and signature
    def inner(*args, **kwargs):
        bound_args = sig.bind(*args, **kwargs)

        event_data = {
            "ip_address": _get_remote_addr(),
            "browser_fingerprint": _get_browser_fingerprint(),
            **bound_args.arguments,
        }
        events_api_client.create_event(fn.__name__, event_data)

    return cast(T, inner)


class Events:
    @event_creator
    def sucessful_login(*, user_id) -> None:
        pass

    @event_creator
    def update_user_email(*, user_id, updated_by_id, original_email_address, new_email_address) -> None:
        pass

    @event_creator
    def update_user_mobile_number(*, user_id, updated_by_id, original_mobile_number, new_mobile_number) -> None:
        pass

    @event_creator
    def remove_user_from_service(*, user_id, removed_by_id, service_id) -> None:
        pass

    @event_creator
    def add_user_to_service(*, user_id, invited_by_id, service_id, ui_permissions) -> None:
        pass

    @event_creator
    def set_user_permissions(*, user_id, service_id, original_ui_permissions, new_ui_permissions, set_by_id) -> None:
        pass

    @event_creator
    def set_organisation_user_permissions(
        *,
        user_id,
        organisation_id,
        original_permissions,
        new_permissions,
        set_by_id,
    ) -> None:
        pass

    @event_creator
    def archive_user(*, user_id, user_email_address, archived_by_id) -> None:
        pass

    @event_creator
    def archive_service(*, service_id, archived_by_id) -> None:
        pass

    @event_creator
    def update_email_branding(*, email_branding_id, updated_by_id, old_email_branding) -> None:
        pass

    @event_creator
    def update_letter_branding(*, letter_branding_id, updated_by_id, old_letter_branding) -> None:
        pass

    @event_creator
    def set_inbound_sms_on(*, user_id, service_id, inbound_number_id) -> None:
        pass

    @event_creator
    def remove_platform_admin(*, user_id, removed_by_id) -> None:
        pass


# This might not be totally correct depending on proxy setup
def _get_remote_addr():
    # If other headers are required (or this one no is longer needed) update the docs:
    # https://github.com/alphagov/notifications-manuals/wiki/Request-headers-used
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0]
    return request.remote_addr


def _get_browser_fingerprint():
    # at some point this may be hashed?
    return {
        "browser": request.user_agent.browser,
        "platform": request.user_agent.platform,
        "version": request.user_agent.version,
        "user_agent_string": request.user_agent.string,
    }

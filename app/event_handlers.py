from flask import request

from app import events_api_client


def on_user_logged_in(_sender, user):
    _send_event('sucessful_login', user_id=user.id)


def create_email_change_event(user_id, updated_by_id, original_email_address, new_email_address):
    _send_event(
        'update_user_email',
        user_id=user_id,
        updated_by_id=updated_by_id,
        original_email_address=original_email_address,
        new_email_address=new_email_address)


def create_mobile_number_change_event(user_id, updated_by_id, original_mobile_number, new_mobile_number):
    _send_event(
        'update_user_mobile_number',
        user_id=user_id,
        updated_by_id=updated_by_id,
        original_mobile_number=original_mobile_number,
        new_mobile_number=new_mobile_number)


def create_remove_user_from_service_event(user_id, removed_by_id, service_id):
    _send_event(
        'remove_user_from_service',
        user_id=user_id,
        removed_by_id=removed_by_id,
        service_id=service_id
    )


def create_add_user_to_service_event(user_id, invited_by_id, service_id):
    _send_event(
        'add_user_to_service',
        user_id=user_id,
        invited_by_id=invited_by_id,
        service_id=service_id
    )


def create_archive_user_event(user_id, archived_by_id):
    _send_event(
        'archive_user',
        user_id=user_id,
        archived_by_id=archived_by_id)


def create_broadcast_account_type_change_event(
    service_id,
    changed_by_id,
    service_mode,
    broadcast_channel,
    provider_restriction,
):
    _send_event(
        'change_broadcast_account_type',
        service_id=service_id,
        changed_by_id=changed_by_id,
        service_mode=service_mode,
        broadcast_channel=broadcast_channel,
        provider_restriction=provider_restriction
    )


def create_suspend_service_event(
    service_id,
    suspended_by_id,
):
    _send_event(
        'suspend_service',
        service_id=service_id,
        suspended_by_id=suspended_by_id,
    )


def create_archive_service_event(
    service_id,
    archived_by_id,
):
    _send_event(
        'archive_service',
        service_id=service_id,
        archived_by_id=archived_by_id,
    )


def _send_event(event_type, **kwargs):
    event_data = _construct_event_data(request)
    event_data.update(kwargs)

    events_api_client.create_event(event_type, event_data)


def _construct_event_data(request):
    return {'ip_address': _get_remote_addr(request),
            'browser_fingerprint': _get_browser_fingerprint(request)}


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
    finger_print = {'browser': browser,
                    'platform': platform,
                    'version': version,
                    'user_agent_string': user_agent_string}

    return finger_print

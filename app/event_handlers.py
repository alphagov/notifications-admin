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

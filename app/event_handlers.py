from flask import request

from app import events_api_client


def on_user_logged_in(sender, user):
    _send_event(sender, event_type='sucessful_login', user=user)


def _send_event(sender, **kwargs):
    if not kwargs.get('event_type'):
        return

    event_data = _construct_event_data(request)

    if kwargs.get('user'):
        event_data['user_id'] = kwargs.get('user').id

    events_api_client.create_event(kwargs['event_type'], event_data)


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

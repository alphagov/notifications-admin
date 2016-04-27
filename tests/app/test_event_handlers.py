from unittest.mock import ANY

from app.event_handlers import (
    on_user_logged_in,
    on_user_login_confirmed
)


def test_on_user_logged_in_calls_events_api(app_, api_user_active, mock_events):

    with app_.test_request_context():
        on_user_logged_in(app_, api_user_active)
        mock_events.assert_called_with('sucessful_login',
                                       {'browser_fingerprint':
                                        {'browser': ANY, 'version': ANY, 'platform': ANY, 'user_agent_string': ''},
                                        'ip_address': ANY, 'user_id': str(api_user_active.id)})


def test_on_user_login_confirmed_in_calls_events_api(app_, api_user_active, mock_events):

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)  # user must have been logged in already.

            on_user_login_confirmed(app_)
            mock_events.assert_called_with('sucessful_login_remember_me',
                                           {'browser_fingerprint':
                                            {'browser': ANY, 'version': ANY, 'platform': ANY, 'user_agent_string': ''},
                                            'ip_address': ANY, 'user_id': str(api_user_active.id)})

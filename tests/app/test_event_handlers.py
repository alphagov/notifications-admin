import uuid
from unittest.mock import ANY

from app.event_handlers import (
    create_email_change_event,
    create_mobile_number_change_event,
    on_user_logged_in,
)
from app.models.user import User


def test_on_user_logged_in_calls_events_api(app_, api_user_active, mock_events):

    with app_.test_request_context():
        on_user_logged_in(app_, User(api_user_active))
        mock_events.assert_called_with('sucessful_login',
                                       {'browser_fingerprint':
                                        {'browser': ANY, 'version': ANY, 'platform': ANY, 'user_agent_string': ''},
                                        'ip_address': ANY, 'user_id': str(api_user_active['id'])})


def test_create_email_change_event_calls_events_api(app_, mock_events):
    user_id = str(uuid.uuid4())
    updated_by_id = str(uuid.uuid4())

    with app_.test_request_context():
        create_email_change_event(user_id, updated_by_id, 'original@example.com', 'new@example.com')

        mock_events.assert_called_with('update_user_email',
                                       {'browser_fingerprint':
                                        {'browser': ANY, 'version': ANY, 'platform': ANY, 'user_agent_string': ''},
                                        'ip_address': ANY,
                                        'user_id': user_id,
                                        'updated_by_id': updated_by_id,
                                        'original_email_address': 'original@example.com',
                                        'new_email_address': 'new@example.com'})


def test_create_mobile_number_change_event_calls_events_api(app_, mock_events):
    user_id = str(uuid.uuid4())
    updated_by_id = str(uuid.uuid4())

    with app_.test_request_context():
        create_mobile_number_change_event(user_id, updated_by_id, '07700900000', '07700900999')

        mock_events.assert_called_with('update_user_mobile_number',
                                       {'browser_fingerprint':
                                        {'browser': ANY, 'version': ANY, 'platform': ANY, 'user_agent_string': ''},
                                        'ip_address': ANY,
                                        'user_id': user_id,
                                        'updated_by_id': updated_by_id,
                                        'original_mobile_number': '07700900000',
                                        'new_mobile_number': '07700900999'})

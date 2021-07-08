import uuid
from unittest.mock import ANY

from app.event_handlers import (
    create_add_user_to_service_event,
    create_archive_user_event,
    create_broadcast_account_type_change_event,
    create_email_change_event,
    create_mobile_number_change_event,
    create_remove_user_from_service_event,
    create_suspend_service_event,
    on_user_logged_in,
)
from app.models.user import User


def test_on_user_logged_in_calls_events_api(notify_admin, api_user_active, mock_events):

    with notify_admin.test_request_context():
        on_user_logged_in(notify_admin, User(api_user_active))
        mock_events.assert_called_with('sucessful_login',
                                       {'browser_fingerprint':
                                        {'browser': ANY, 'version': ANY, 'platform': ANY, 'user_agent_string': ''},
                                        'ip_address': ANY, 'user_id': str(api_user_active['id'])})


def test_create_email_change_event_calls_events_api(notify_admin, mock_events):
    user_id = str(uuid.uuid4())
    updated_by_id = str(uuid.uuid4())

    with notify_admin.test_request_context():
        create_email_change_event(user_id, updated_by_id, 'original@example.com', 'new@example.com')

        mock_events.assert_called_with('update_user_email',
                                       {'browser_fingerprint':
                                        {'browser': ANY, 'version': ANY, 'platform': ANY, 'user_agent_string': ''},
                                        'ip_address': ANY,
                                        'user_id': user_id,
                                        'updated_by_id': updated_by_id,
                                        'original_email_address': 'original@example.com',
                                        'new_email_address': 'new@example.com'})


def test_create_add_user_to_service_event_calls_events_api(notify_admin, mock_events):
    user_id = str(uuid.uuid4())
    invited_by_id = str(uuid.uuid4())
    service_id = str(uuid.uuid4())

    with notify_admin.test_request_context():
        create_add_user_to_service_event(user_id, invited_by_id, service_id)

        mock_events.assert_called_with(
            'add_user_to_service',
            {
                'browser_fingerprint': {'browser': ANY, 'version': ANY, 'platform': ANY, 'user_agent_string': ''},
                'ip_address': ANY,
                'user_id': user_id,
                'invited_by_id': invited_by_id,
                'service_id': service_id,
            }
        )


def test_create_remove_user_from_service_event_calls_events_api(notify_admin, mock_events):
    user_id = str(uuid.uuid4())
    removed_by_id = str(uuid.uuid4())
    service_id = str(uuid.uuid4())

    with notify_admin.test_request_context():
        create_remove_user_from_service_event(user_id, removed_by_id, service_id)

        mock_events.assert_called_with(
            'remove_user_from_service',
            {
                'browser_fingerprint': {'browser': ANY, 'version': ANY, 'platform': ANY, 'user_agent_string': ''},
                'ip_address': ANY,
                'user_id': user_id,
                'removed_by_id': removed_by_id,
                'service_id': service_id,
            }
        )


def test_create_mobile_number_change_event_calls_events_api(notify_admin, mock_events):
    user_id = str(uuid.uuid4())
    updated_by_id = str(uuid.uuid4())

    with notify_admin.test_request_context():
        create_mobile_number_change_event(user_id, updated_by_id, '07700900000', '07700900999')

        mock_events.assert_called_with('update_user_mobile_number',
                                       {'browser_fingerprint':
                                        {'browser': ANY, 'version': ANY, 'platform': ANY, 'user_agent_string': ''},
                                        'ip_address': ANY,
                                        'user_id': user_id,
                                        'updated_by_id': updated_by_id,
                                        'original_mobile_number': '07700900000',
                                        'new_mobile_number': '07700900999'})


def test_create_archive_user_event_calls_events_api(notify_admin, mock_events):
    user_id = str(uuid.uuid4())
    archived_by_id = str(uuid.uuid4())

    with notify_admin.test_request_context():
        create_archive_user_event(user_id, archived_by_id)

        mock_events.assert_called_with('archive_user',
                                       {'browser_fingerprint':
                                        {'browser': ANY, 'version': ANY, 'platform': ANY, 'user_agent_string': ''},
                                        'ip_address': ANY,
                                        'user_id': user_id,
                                        'archived_by_id': archived_by_id})


def test_create_broadcast_account_type_change_event(notify_admin, mock_events):
    service_id = str(uuid.uuid4())
    changed_by_id = str(uuid.uuid4())

    with notify_admin.test_request_context():
        create_broadcast_account_type_change_event(
            service_id,
            changed_by_id,
            'training',
            'severe',
            None)

        mock_events.assert_called_with('change_broadcast_account_type',
                                       {'browser_fingerprint':
                                        {'browser': ANY, 'version': ANY, 'platform': ANY, 'user_agent_string': ''},
                                        'ip_address': ANY,
                                        'service_id': service_id,
                                        'changed_by_id': changed_by_id,
                                        'service_mode': 'training',
                                        'broadcast_channel': 'severe',
                                        'provider_restriction': None})


def test_suspend_service(client, mock_events):
    service_id = str(uuid.uuid4())
    suspended_by_id = str(uuid.uuid4())

    create_suspend_service_event(
        service_id,
        suspended_by_id,
    )

    mock_events.assert_called_with(
        'suspend_service',
        {'browser_fingerprint': {'browser': ANY, 'version': ANY, 'platform': ANY, 'user_agent_string': ''},
         'ip_address': ANY,
         'service_id': service_id,
         'suspended_by_id': suspended_by_id},
    )

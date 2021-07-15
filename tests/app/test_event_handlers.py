import uuid
from unittest.mock import ANY

from app.event_handlers import (
    create_add_user_to_service_event,
    create_archive_service_event,
    create_archive_user_event,
    create_broadcast_account_type_change_event,
    create_email_change_event,
    create_mobile_number_change_event,
    create_remove_user_from_service_event,
    create_resume_service_event,
    create_set_user_permissions_event,
    create_suspend_service_event,
    on_user_logged_in,
)
from app.models.user import User


def event_dict(**extra):
    return {
       'browser_fingerprint': {'browser': ANY, 'version': ANY, 'platform': ANY, 'user_agent_string': ''},
       'ip_address': ANY,
       **extra
    }


def test_on_user_logged_in_calls_events_api(client, api_user_active, mock_events):
    on_user_logged_in('_notify_admin', User(api_user_active))

    mock_events.assert_called_with('sucessful_login', event_dict(
        user_id=str(api_user_active['id'])
    ))


def test_create_email_change_event_calls_events_api(client, mock_events):
    kwargs = {
        "user_id": str(uuid.uuid4()),
        "updated_by_id": str(uuid.uuid4()),
        "original_email_address": 'original@example.com',
        "new_email_address": 'new@example.com'
    }

    create_email_change_event(**kwargs)
    mock_events.assert_called_with('update_user_email', event_dict(**kwargs))


def test_create_add_user_to_service_event_calls_events_api(client, mock_events):
    kwargs = {
        "user_id": str(uuid.uuid4()),
        "invited_by_id": str(uuid.uuid4()),
        "service_id": str(uuid.uuid4()),
        "admin_roles": {'manage_templates'},
    }

    create_add_user_to_service_event(**kwargs)
    mock_events.assert_called_with('add_user_to_service', event_dict(**kwargs))


def test_create_remove_user_from_service_event_calls_events_api(client, mock_events):
    kwargs = {
        "user_id": str(uuid.uuid4()),
        "removed_by_id": str(uuid.uuid4()),
        "service_id": str(uuid.uuid4())
    }

    create_remove_user_from_service_event(**kwargs)
    mock_events.assert_called_with('remove_user_from_service', event_dict(**kwargs))


def test_create_mobile_number_change_event_calls_events_api(client, mock_events):
    kwargs = {
        "user_id": str(uuid.uuid4()),
        "updated_by_id": str(uuid.uuid4()),
        "original_mobile_number": '07700900000',
        "new_mobile_number": '07700900999'
    }

    create_mobile_number_change_event(**kwargs)
    mock_events.assert_called_with('update_user_mobile_number', event_dict(**kwargs))


def test_create_archive_user_event_calls_events_api(client, mock_events):
    kwargs = {
        "user_id": str(uuid.uuid4()),
        "archived_by_id": str(uuid.uuid4())
    }

    create_archive_user_event(**kwargs)
    mock_events.assert_called_with('archive_user', event_dict(**kwargs))


def test_create_broadcast_account_type_change_event(client, mock_events):
    kwargs = {
        "service_id": str(uuid.uuid4()),
        "changed_by_id": str(uuid.uuid4()),
        "service_mode": 'training',
        "broadcast_channel": 'severe',
        "provider_restriction": None
    }

    create_broadcast_account_type_change_event(**kwargs)
    mock_events.assert_called_with('change_broadcast_account_type', event_dict(**kwargs))


def test_suspend_service(client, mock_events):
    kwargs = {
        "service_id": str(uuid.uuid4()),
        "suspended_by_id": str(uuid.uuid4())
    }

    create_suspend_service_event(**kwargs)
    mock_events.assert_called_with('suspend_service', event_dict(**kwargs))


def test_archive_service(client, mock_events):
    kwargs = {
        "service_id": str(uuid.uuid4()),
        "archived_by_id": str(uuid.uuid4())
    }

    create_archive_service_event(**kwargs)
    mock_events.assert_called_with('archive_service', event_dict(**kwargs))


def test_resume_service(client, mock_events):
    kwargs = {
        "service_id": str(uuid.uuid4()),
        "resumed_by_id": str(uuid.uuid4())
    }

    create_resume_service_event(**kwargs)
    mock_events.assert_called_with('resume_service', event_dict(**kwargs))


def test_set_user_permissions(client, mock_events):
    kwargs = {
        "user_id": str(uuid.uuid4()),
        "service_id": str(uuid.uuid4()),
        "original_admin_roles": set("manage_templates"),
        "new_admin_roles": set("view_activity"),
        "set_by_id": str(uuid.uuid4()),
    }

    create_set_user_permissions_event(**kwargs)
    mock_events.assert_called_with('set_user_permissions', event_dict(**kwargs))

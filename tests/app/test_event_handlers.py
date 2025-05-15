import uuid
from unittest.mock import ANY

from app.event_handlers import Events


def event_dict(**extra):
    return {
        "browser_fingerprint": {"browser": ANY, "version": ANY, "platform": ANY, "user_agent_string": ANY},
        "ip_address": ANY,
        **extra,
    }


def test_on_user_logged_in_calls_events_api(client_request, api_user_active, mock_events):
    Events.sucessful_login(user_id=api_user_active["id"])
    mock_events.assert_called_with("sucessful_login", event_dict(user_id=str(api_user_active["id"])))


def test_create_email_change_event_calls_events_api(client_request, mock_events):
    kwargs = {
        "user_id": str(uuid.uuid4()),
        "updated_by_id": str(uuid.uuid4()),
        "original_email_address": "original@example.com",
        "new_email_address": "new@example.com",
    }

    Events.update_user_email(**kwargs)
    mock_events.assert_called_with("update_user_email", event_dict(**kwargs))


def test_create_add_user_to_service_event_calls_events_api(client_request, mock_events):
    kwargs = {
        "user_id": str(uuid.uuid4()),
        "invited_by_id": str(uuid.uuid4()),
        "service_id": str(uuid.uuid4()),
        "ui_permissions": {"manage_templates"},
    }

    Events.add_user_to_service(**kwargs)
    mock_events.assert_called_with("add_user_to_service", event_dict(**kwargs))


def test_create_remove_user_from_service_event_calls_events_api(client_request, mock_events):
    kwargs = {"user_id": str(uuid.uuid4()), "removed_by_id": str(uuid.uuid4()), "service_id": str(uuid.uuid4())}

    Events.remove_user_from_service(**kwargs)
    mock_events.assert_called_with("remove_user_from_service", event_dict(**kwargs))


def test_create_mobile_number_change_event_calls_events_api(client_request, mock_events):
    kwargs = {
        "user_id": str(uuid.uuid4()),
        "updated_by_id": str(uuid.uuid4()),
        "original_mobile_number": "07700900000",
        "new_mobile_number": "07700900999",
    }

    Events.update_user_mobile_number(**kwargs)
    mock_events.assert_called_with("update_user_mobile_number", event_dict(**kwargs))


def test_create_archive_user_event_calls_events_api(client_request, mock_events):
    kwargs = {"user_id": str(uuid.uuid4()), "user_email_address": "user@gov.uk", "archived_by_id": str(uuid.uuid4())}

    Events.archive_user(**kwargs)
    mock_events.assert_called_with("archive_user", event_dict(**kwargs))


def test_archive_service(client_request, mock_events):
    kwargs = {"service_id": str(uuid.uuid4()), "archived_by_id": str(uuid.uuid4())}

    Events.archive_service(**kwargs)
    mock_events.assert_called_with("archive_service", event_dict(**kwargs))


def test_set_user_permissions(client_request, mock_events):
    kwargs = {
        "user_id": str(uuid.uuid4()),
        "service_id": str(uuid.uuid4()),
        "original_ui_permissions": set("manage_templates"),
        "new_ui_permissions": set("view_activity"),
        "set_by_id": str(uuid.uuid4()),
    }

    Events.set_user_permissions(**kwargs)
    mock_events.assert_called_with("set_user_permissions", event_dict(**kwargs))

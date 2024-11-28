import json
import uuid
from datetime import datetime
from unittest.mock import Mock

import pytest
from flask import url_for
from freezegun import freeze_time
from notifications_python_client.errors import HTTPError

from app.main.views.conversation import get_user_number
from tests.conftest import (
    SERVICE_ONE_ID,
    _template,
    create_notifications,
    normalize_spaces,
)

INV_PARENT_FOLDER_ID = "7e979e79-d970-43a5-ac69-b625a8d147b0"
VIS_PARENT_FOLDER_ID = "bbbb222b-2b22-2b22-222b-b222b22b2222"


def test_get_user_phone_number_when_only_inbound_exists(notify_admin, mocker):
    mock_get_inbound_sms = mocker.patch(
        "app.main.views.conversation.service_api_client.get_inbound_sms_by_id",
        return_value={"user_number": "4407900900123", "notify_number": "07900000002"},
    )
    mock_get_notification = mocker.patch(
        "app.main.views.conversation.notification_api_client.get_notification",
        side_effect=HTTPError(response=Mock(status_code=404)),
    )
    assert get_user_number("service", "notification") == "07900 900123"
    mock_get_inbound_sms.assert_called_once_with("service", "notification")
    assert mock_get_notification.called is False


def test_get_user_phone_number_when_only_outbound_exists(notify_admin, mocker):
    mock_get_inbound_sms = mocker.patch(
        "app.main.views.conversation.service_api_client.get_inbound_sms_by_id",
        side_effect=HTTPError(response=Mock(status_code=404)),
    )
    mock_get_notification = mocker.patch(
        "app.main.views.conversation.notification_api_client.get_notification", return_value={"to": "14157711401"}
    )
    assert get_user_number("service", "notification") == "+1 415-771-1401"
    mock_get_inbound_sms.assert_called_once_with("service", "notification")
    mock_get_notification.assert_called_once_with("service", "notification")


def test_get_user_phone_number_raises_if_both_api_requests_fail(notify_admin, mocker):
    mock_get_inbound_sms = mocker.patch(
        "app.main.views.conversation.service_api_client.get_inbound_sms_by_id",
        side_effect=HTTPError(response=Mock(status_code=404)),
    )
    mock_get_notification = mocker.patch(
        "app.main.views.conversation.notification_api_client.get_notification",
        side_effect=HTTPError(response=Mock(status_code=404)),
    )
    with pytest.raises(HTTPError):
        get_user_number("service", "notification")
    mock_get_inbound_sms.assert_called_once_with("service", "notification")
    mock_get_notification.assert_called_once_with("service", "notification")


@pytest.mark.parametrize(
    "outbound_redacted, expected_outbound_content",
    [
        (True, "Hello hidden"),
        (False, "Hello Jo"),
    ],
)
@freeze_time("2012-01-01 00:00:00")
def test_view_conversation(
    client_request,
    mocker,
    mock_get_inbound_sms_by_id_with_no_messages,
    mock_get_notification,
    fake_uuid,
    outbound_redacted,
    expected_outbound_content,
    mock_get_inbound_sms,
):
    notifications = create_notifications(
        content="Hello ((name))",
        personalisation={"name": "Jo"},
        redact_personalisation=outbound_redacted,
    )
    mock = mocker.patch("app.models.notification.Notifications._get_items", return_value=notifications)

    page = client_request.get(
        "main.conversation",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one("title").text) == "Received text message – service one – GOV.UK Notify"
    assert normalize_spaces(page.select_one("h1").text) == "07123 456789"

    messages = page.select(".sms-message-wrapper")
    statuses = page.select(".sms-message-status")

    assert len(messages) == 13
    assert len(statuses) == 13

    for index, expected in enumerate(
        [
            (
                "message-8",
                "yesterday at 2:59pm",
            ),
            (
                "message-7",
                "yesterday at 2:59pm",
            ),
            (
                "message-6",
                "yesterday at 4:59pm",
            ),
            (
                "message-5",
                "yesterday at 6:59pm",
            ),
            (
                "message-4",
                "yesterday at 8:59pm",
            ),
            (
                "message-3",
                "yesterday at 10:59pm",
            ),
            (
                "message-2",
                "yesterday at 10:59pm",
            ),
            (
                "message-1",
                "yesterday at 11:00pm",
            ),
            (
                expected_outbound_content,
                "yesterday at midnight",
            ),
            (
                expected_outbound_content,
                "yesterday at midnight",
            ),
            (
                expected_outbound_content,
                "yesterday at midnight",
            ),
            (
                expected_outbound_content,
                "yesterday at midnight",
            ),
            (
                expected_outbound_content,
                "yesterday at midnight",
            ),
        ]
    ):
        assert (
            normalize_spaces(messages[index].text),
            normalize_spaces(statuses[index].text),
        ) == expected

    mock_get_inbound_sms.assert_called_once_with(SERVICE_ONE_ID, user_number="07123 456789")
    mock.assert_called_once_with(SERVICE_ONE_ID, to="07123 456789", template_type="sms")


def test_view_conversation_updates(
    client_request,
    mocker,
    fake_uuid,
    mock_get_notification,
):
    mocker.patch(
        "app.main.views.conversation.service_api_client.get_inbound_sms_by_id",
        side_effect=HTTPError(response=Mock(status_code=404)),
    )
    mock_get_partials = mocker.patch(
        "app.main.views.conversation.get_conversation_partials", return_value={"messages": "foo"}
    )

    response = client_request.get_response(
        "json_updates.conversation_updates",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    assert json.loads(response.get_data(as_text=True)) == {"messages": "foo"}

    mock_get_partials.assert_called_once_with(SERVICE_ONE_ID, "07123 456789")


@freeze_time("2012-01-01 00:00:00")
def test_view_conversation_with_empty_inbound(
    client_request,
    mocker,
    mock_get_inbound_sms_by_id_with_no_messages,
    mock_get_notification,
    mock_get_notifications_with_no_notifications,
    fake_uuid,
):
    mock_get_inbound_sms = mocker.patch(
        "app.models.notification.InboundSMSMessages._get_items",
        return_value={
            "has_next": False,
            "data": [
                {
                    "user_number": "07900000001",
                    "notify_number": "07900000002",
                    "content": "",
                    "created_at": datetime.utcnow().isoformat(),
                    "id": fake_uuid,
                }
            ],
        },
    )

    page = client_request.get(
        "main.conversation",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        _test_page_title=False,
    )

    messages = page.select(".sms-message-wrapper")
    assert len(messages) == 1
    assert mock_get_inbound_sms.called is True


def test_conversation_links_to_reply(
    client_request,
    fake_uuid,
    mock_get_inbound_sms_by_id_with_no_messages,
    mock_get_notification,
    mock_get_notifications,
    mock_get_inbound_sms,
):
    page = client_request.get(
        "main.conversation",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        _test_page_title=False,
    )

    assert page.select("main p")[-1].select_one("a")["href"] == (
        url_for(
            ".conversation_reply",
            service_id=SERVICE_ONE_ID,
            notification_id=fake_uuid,
        )
    )


def test_conversation_reply_shows_link_to_add_templates_if_service_has_no_templates(
    client_request,
    fake_uuid,
    mock_get_service_templates_when_no_templates_exist,
    mock_get_template_folders,
):
    page = client_request.get(
        "main.conversation_reply",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    page_text = page.select_one("p.bottom-gutter").text
    assert normalize_spaces(page_text) == "You need a template before you can send text messages."

    link = page.select_one("a.govuk-button[role=button]")
    assert normalize_spaces(link.text) == "Add a new template"
    assert link["href"] == url_for("main.choose_template", service_id=SERVICE_ONE_ID, initial_state="add-new-template")


def test_conversation_reply_shows_templates(
    client_request, fake_uuid, mocker, mock_get_template_folders, active_user_with_permissions, service_one
):
    template_two_id = "5b35cf78-a07e-4618-a7d1-c328e53d63d8"
    all_templates = {
        "data": [
            _template("sms", "sms_template_one", parent=INV_PARENT_FOLDER_ID),
            _template("sms", "sms_template_two", template_id=template_two_id),
            _template("sms", "sms_template_three", parent=VIS_PARENT_FOLDER_ID),
            _template("letter", "letter_template_one"),
        ]
    }
    mocker.patch("app.service_api_client.get_service_templates", return_value=all_templates)
    mock_get_template_folders.return_value = [
        {"name": "Parent 1 - invisible", "id": INV_PARENT_FOLDER_ID, "parent_id": None, "users_with_permission": []},
        {
            "name": "Parent 2 - visible",
            "id": VIS_PARENT_FOLDER_ID,
            "parent_id": None,
            "users_with_permission": [active_user_with_permissions["id"]],
        },
    ]
    page = client_request.get(
        "main.conversation_reply",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    link = page.select(".template-list-item-without-ancestors")
    assert normalize_spaces(link[0].text) == "Folder Parent 2 - visible 1 template"
    assert normalize_spaces(link[1].text) == "sms_template_two Text message template"

    assert link[0].select_one("a")["href"] == url_for(
        "main.conversation_reply",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        from_folder=VIS_PARENT_FOLDER_ID,
    )

    assert link[1].select_one("a")["href"] == url_for(
        "main.conversation_reply_with_template",
        service_id=SERVICE_ONE_ID,
        template_id=template_two_id,
        notification_id=fake_uuid,
        from_folder=None,
    )


def test_conversation_reply_shows_live_search(
    client_request,
    fake_uuid,
    mock_get_service_templates,
    mock_get_template_folders,
):
    page = client_request.get(
        "main.conversation_reply",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    assert page.select(".live-search")


def test_conversation_reply_redirects_with_phone_number_from_notification(
    client_request,
    fake_uuid,
    mock_get_inbound_sms_by_id_with_no_messages,
    mock_get_notification,
    mock_get_service_template,
):
    page = client_request.get(
        "main.conversation_reply_with_template",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        template_id=fake_uuid,
        _follow_redirects=True,
    )

    for element, expected_text in [
        ("h1", "Preview of ‘Two week reminder’"),
        (".sms-message-recipient", "To: 07123 456789"),
        (".sms-message-wrapper", "service one: Template <em>content</em> with & entity"),
    ]:
        assert normalize_spaces(page.select_one(element).text) == expected_text


def test_conversation_reply_with_template_adds_values_to_session(
    client_request,
    fake_uuid,
    mock_get_inbound_sms_by_id_with_no_messages,
    mock_get_notification,
    mock_get_service_template,
):
    client_request.get(
        "main.conversation_reply_with_template",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        template_id=fake_uuid,
        from_folder="abcd",
        _follow_redirects=True,
    )

    with client_request.session_transaction() as session:
        assert session["recipient"] == "07123 456789"
        assert session["placeholders"] == {"phone number": "07123 456789"}
        assert session["from_inbound_sms_details"] == {"from_folder": "abcd", "notification_id": fake_uuid}


def test_conversation_reply_back_link_when_viewing_top_level_templates(
    client_request,
    fake_uuid,
    mock_get_template_folders,
    mock_get_service_templates,
):
    page = client_request.get(
        "main.conversation_reply",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    assert page.select_one(".govuk-back-link")["href"] == url_for(
        "main.conversation", service_id=SERVICE_ONE_ID, notification_id=fake_uuid
    )


def test_conversation_reply_back_link_when_viewing_nested_templates(
    client_request,
    fake_uuid,
    active_user_with_permissions,
    mock_get_template_folders,
    mock_get_service_templates,
):
    sub_folder_id = uuid.uuid4()
    parent_folder_id = uuid.uuid4()
    template_folders = [
        {
            "id": str(parent_folder_id),
            "name": "Parent folder",
            "service_id": SERVICE_ONE_ID,
            "parent_id": None,
            "users_with_permission": [active_user_with_permissions["id"]],
        },
        {
            "id": str(sub_folder_id),
            "name": "Sub-folder",
            "service_id": SERVICE_ONE_ID,
            "parent_id": str(parent_folder_id),
            "users_with_permission": [active_user_with_permissions["id"]],
        },
    ]
    mock_get_template_folders.return_value = template_folders

    # The back link when viewing a sub-folder takes you to the parent folder
    page = client_request.get(
        "main.conversation_reply",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        from_folder=str(sub_folder_id),
    )
    assert page.select_one(".govuk-back-link")["href"] == url_for(
        "main.conversation_reply",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        from_folder=str(parent_folder_id),
    )
    # The back link when viewing a top-level folder takes you to the top-level templates page
    page = client_request.get(
        "main.conversation_reply",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        from_folder=str(parent_folder_id),
    )
    assert page.select_one(".govuk-back-link")["href"] == url_for(
        "main.conversation_reply", service_id=SERVICE_ONE_ID, notification_id=fake_uuid
    )


def test_get_user_phone_number_when_not_a_standard_phone_number(notify_admin, mocker):
    mocker.patch(
        "app.main.views.conversation.service_api_client.get_inbound_sms_by_id",
        return_value={"user_number": "ALPHANUM3R1C", "notify_number": "07900000002"},
    )
    mocker.patch(
        "app.main.views.conversation.notification_api_client.get_notification",
        side_effect=HTTPError,
    )
    assert get_user_number("service", "notification") == "ALPHANUM3R1C"

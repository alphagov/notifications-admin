import uuid
from collections import namedtuple

import pytest

from app.notify_client.notification_api_client import NotificationApiClient
from tests import notification_json, single_notification_json


@pytest.mark.parametrize(
    "arguments,expected_call",
    [
        ({}, {"url": "/service/abcd1234/notifications", "params": {}}),
        ({"page": 99}, {"url": "/service/abcd1234/notifications", "params": {"page": 99}}),
        ({"include_jobs": False}, {"url": "/service/abcd1234/notifications", "params": {"include_jobs": False}}),
        (
            {"include_from_test_key": True},
            {"url": "/service/abcd1234/notifications", "params": {"include_from_test_key": True}},
        ),
        (
            {"page": 48, "limit_days": 3},
            {"url": "/service/abcd1234/notifications", "params": {"page": 48, "limit_days": 3}},
        ),
        ({"job_id": "efgh5678"}, {"url": "/service/abcd1234/job/efgh5678/notifications", "params": {}}),
        (
            {"job_id": "efgh5678", "page": 48},
            {"url": "/service/abcd1234/job/efgh5678/notifications", "params": {"page": 48}},
        ),
        (
            {"job_id": "efgh5678", "page": 48, "limit_days": 3},
            {"url": "/service/abcd1234/job/efgh5678/notifications", "params": {"page": 48}},
        ),
    ],
)
def test_client_gets_notifications_for_service_and_job_by_page(mocker, arguments, expected_call):
    mock_get = mocker.patch("app.notify_client.notification_api_client.NotificationApiClient.get")
    NotificationApiClient(mocker.MagicMock()).get_notifications_for_service("abcd1234", **arguments)
    mock_get.assert_called_once_with(**expected_call)


@pytest.mark.parametrize(
    "arguments,expected_call",
    [
        ({"to": "0793433"}, {"url": "/service/abcd1234/notifications", "data": {"to": "0793433"}}),
        (
            {"to": "0793433", "job_id": "efgh5678"},
            {"url": "/service/abcd1234/job/efgh5678/notifications", "data": {"to": "0793433"}},
        ),
        (
            {"to": "0793433", "page": 99},
            {"url": "/service/abcd1234/notifications", "data": {"to": "0793433", "page": 99}},
        ),
        (
            {"to": "0793433", "limit_days": 3},
            {"url": "/service/abcd1234/notifications", "data": {"to": "0793433", "limit_days": 3}},
        ),
        (
            {"to": "0793433", "job_id": "efgh5678", "limit_days": 3},
            {"url": "/service/abcd1234/job/efgh5678/notifications", "data": {"to": "0793433"}},
        ),
    ],
)
def test_client_gets_notifications_for_service_and_job_by_page_posts_for_to(mocker, arguments, expected_call):
    mock_post = mocker.patch("app.notify_client.notification_api_client.NotificationApiClient.post")
    NotificationApiClient(mocker.MagicMock()).get_notifications_for_service("abcd1234", **arguments)
    mock_post.assert_called_once_with(**expected_call)


@pytest.mark.parametrize(
    "arguments,expected_call",
    [
        ({}, {"url": "/service/abcd1234/notifications/csv", "params": {}}),
        ({"page": 99}, {"url": "/service/abcd1234/notifications/csv", "params": {"page": 99}}),
        (
            {"job_id": "efgh5678"},
            {"url": "/service/abcd1234/job/efgh5678/notifications", "params": {"format_for_csv": True}},
        ),
        (
            {"job_id": "efgh5678", "page_size": 10},
            {
                "url": "/service/abcd1234/job/efgh5678/notifications",
                "params": {"page_size": 10, "format_for_csv": True},
            },
        ),
        (
            {
                "page": 48,
                "limit_days": 3,
                "older_than": "5678",
                "page_size": 10,
                "template_type": "sms",
                "status": "delivered",
            },
            {
                "url": "/service/abcd1234/notifications/csv",
                "params": {
                    "page": 48,
                    "limit_days": 3,
                    "older_than": "5678",
                    "page_size": 10,
                    "template_type": "sms",
                    "status": "delivered",
                },
            },
        ),
    ],
)
def test_client_gets_notifications_for_service_for_csv(mocker, arguments, expected_call):
    mock_get = mocker.patch("app.notify_client.notification_api_client.NotificationApiClient.get")
    NotificationApiClient(mocker.MagicMock()).get_notifications_for_service_for_csv("abcd1234", **arguments)
    mock_get.assert_called_once_with(**expected_call)


def test_send_notification(
    notify_admin,
    client_request,
    active_user_with_permissions,
    mocker,
):
    mock_post = mocker.patch("app.notify_client.notification_api_client.NotificationApiClient.post")
    NotificationApiClient(notify_admin).send_notification(
        "foo", template_id="bar", recipient="07700900001", personalisation=None, sender_id=None
    )
    mock_post.assert_called_once_with(
        url="/service/foo/send-notification",
        data={
            "template_id": "bar",
            "to": "07700900001",
            "personalisation": None,
            "created_by": active_user_with_permissions["id"],
        },
    )


def test_send_precompiled_letter(
    notify_admin,
    client_request,
    active_user_with_permissions,
    mocker,
):
    mock_post = mocker.patch("app.notify_client.notification_api_client.NotificationApiClient.post")
    NotificationApiClient(notify_admin).send_precompiled_letter(
        "abcd-1234", "my_file.pdf", "file-ID", "second", "Bugs Bunny, 12 Hole Avenue, Looney Town"
    )
    mock_post.assert_called_once_with(
        url="/service/abcd-1234/send-pdf-letter",
        data={
            "filename": "my_file.pdf",
            "file_id": "file-ID",
            "created_by": active_user_with_permissions["id"],
            "postage": "second",
            "recipient_address": "Bugs Bunny, 12 Hole Avenue, Looney Town",
        },
    )


def test_get_notification(mocker):
    mock_get = mocker.patch("app.notify_client.notification_api_client.NotificationApiClient.get")
    NotificationApiClient(mocker.MagicMock()).get_notification("foo", "bar")
    mock_get.assert_called_once_with(url="/service/foo/notifications/bar")


@pytest.mark.parametrize(
    "letter_status, expected_status",
    [
        ("created", "accepted"),
        ("sending", "accepted"),
        ("delivered", "received"),
        ("returned-letter", "received"),
        ("technical-failure", "technical-failure"),
    ],
)
def test_get_api_notifications_changes_letter_statuses(mocker, letter_status, expected_status):
    service_id = str(uuid.uuid4())
    sms_notification = single_notification_json(service_id, notification_type="sms", status="created")
    email_notification = single_notification_json(service_id, notification_type="email", status="created")
    letter_notification = single_notification_json(service_id, notification_type="letter", status=letter_status)
    notis = notification_json(service_id=service_id, rows=0)
    notis["notifications"] = [sms_notification, email_notification, letter_notification]

    mocker.patch("app.notify_client.notification_api_client.NotificationApiClient.get", return_value=notis)

    ret = NotificationApiClient(mocker.MagicMock()).get_api_notifications_for_service(service_id)

    assert ret["notifications"][0]["notification_type"] == "sms"
    assert ret["notifications"][1]["notification_type"] == "email"
    assert ret["notifications"][2]["notification_type"] == "letter"
    assert ret["notifications"][0]["status"] == "created"
    assert ret["notifications"][1]["status"] == "created"
    assert ret["notifications"][2]["status"] == expected_status


def test_update_notification_to_cancelled(mocker):
    mock_post = mocker.patch("app.notify_client.notification_api_client.NotificationApiClient.post")
    NotificationApiClient(mocker.MagicMock()).update_notification_to_cancelled("foo", "bar")
    mock_post.assert_called_once_with(
        url="/service/foo/notifications/bar/cancel",
        data={},
    )


def test_get_notification_count_for_job_id(mocker):
    mock_get = mocker.patch("app.notify_client.notification_api_client.NotificationApiClient.get")
    NotificationApiClient(mocker.MagicMock()).get_notification_count_for_job_id(service_id="foo", job_id="bar")
    mock_get.assert_called_once_with(
        url="/service/foo/job/bar/notification_count",
    )


NotificationCountTestCase = namedtuple("NotificationCountTestCase", ["template_type", "limit_days", "expected_count"])


@pytest.mark.parametrize(
    "test_case",
    [
        NotificationCountTestCase(template_type="sms", limit_days=7, expected_count=42),
        NotificationCountTestCase(template_type="email", limit_days=30, expected_count=15),
        NotificationCountTestCase(template_type="letter", limit_days=1, expected_count=0),
    ],
)
def test_get_notifications_count_for_service(mocker, test_case):
    mock_get = mocker.patch("app.notify_client.notification_api_client.NotificationApiClient.get")
    mock_get.return_value = {"notifications_sent_count": test_case.expected_count}

    result = NotificationApiClient(mocker.MagicMock()).get_notifications_count_for_service(
        service_id="foo", template_type=test_case.template_type, limit_days=test_case.limit_days
    )

    mock_get.assert_called_once_with(
        url="/service/foo/notifications/count",
        params={"template_type": test_case.template_type, "limit_days": test_case.limit_days},
    )
    assert result == test_case.expected_count

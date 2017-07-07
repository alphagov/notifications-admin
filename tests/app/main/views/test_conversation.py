import pytest
from bs4 import BeautifulSoup

from flask import (
    url_for,
)
from notifications_python_client.errors import HTTPError
from tests.conftest import (
    SERVICE_ONE_ID,
    normalize_spaces,
    mock_get_notifications,
    mock_get_inbound_sms,
)
from freezegun import freeze_time
from unittest import mock
from app.main.views.conversation import get_user_number


def test_get_user_phone_number_when_only_inbound_exists(mocker):

    mock_get_inbound_sms = mocker.patch(
        'app.main.views.conversation.service_api_client.get_inbound_sms_by_id',
        return_value={
            'user_number': '4407900900123'
        }
    )
    mock_get_notification = mocker.patch(
        'app.main.views.conversation.notification_api_client.get_notification',
        side_effect=HTTPError,
    )
    assert get_user_number('service', 'notification') == '07900 900123'
    mock_get_inbound_sms.assert_called_once_with('service', 'notification')
    assert mock_get_notification.called is False


def test_get_user_phone_number_when_only_outbound_exists(mocker):
    mock_get_inbound_sms = mocker.patch(
        'app.main.views.conversation.service_api_client.get_inbound_sms_by_id',
        side_effect=HTTPError,
    )
    mock_get_notification = mocker.patch(
        'app.main.views.conversation.notification_api_client.get_notification',
        return_value={
            'to': '15550000000'
        }
    )
    assert get_user_number('service', 'notification') == '+1 555-000-0000'
    mock_get_inbound_sms.assert_called_once_with('service', 'notification')
    mock_get_notification.assert_called_once_with('service', 'notification')


def test_get_user_phone_number_raises_if_both_API_requests_fail(mocker):
    mock_get_inbound_sms = mocker.patch(
        'app.main.views.conversation.service_api_client.get_inbound_sms_by_id',
        side_effect=HTTPError,
    )
    mock_get_notification = mocker.patch(
        'app.main.views.conversation.notification_api_client.get_notification',
        side_effect=HTTPError,
    )
    with pytest.raises(HTTPError):
        get_user_number('service', 'notification')
    mock_get_inbound_sms.assert_called_once_with('service', 'notification')
    mock_get_notification.assert_called_once_with('service', 'notification')


@pytest.mark.parametrize('outbound_redacted, expected_outbound_content', [
    (True, 'Hello hidden'),
    (False, 'Hello Jo'),
])
@freeze_time("2012-01-01 00:00:00")
def test_view_conversation(
    client_request,
    mocker,
    api_user_active,
    mock_get_notification,
    fake_uuid,
    outbound_redacted,
    expected_outbound_content,
):

    mock_get_notifications(
        mocker,
        api_user_active,
        template_content='Hello ((name))',
        personalisation={'name': 'Jo'},
        redact_personalisation=outbound_redacted,
    )

    mock_get_inbound_sms(
        mocker
    )

    page = client_request.get(
        'main.conversation',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        _test_page_title=False,
    )

    messages = page.select('.sms-message-wrapper')
    statuses = page.select('.sms-message-status')

    assert len(messages) == 13
    assert len(statuses) == 13

    for index, expected in enumerate([
        (
            'message-8',
            'Failed (sent yesterday at 2:59pm)',
        ),
        (
            'message-7',
            'Failed (sent yesterday at 2:59pm)',
        ),
        (
            'message-6',
            'Failed (sent yesterday at 4:59pm)',
        ),
        (
            'message-5',
            'Failed (sent yesterday at 6:59pm)',
        ),
        (
            'message-4',
            'Failed (sent yesterday at 8:59pm)',
        ),
        (
            'message-3',
            'Failed (sent yesterday at 10:59pm)',
        ),
        (
            'message-2',
            'Failed (sent yesterday at 10:59pm)',
        ),
        (
            'message-1',
            'Failed (sent yesterday at 11:00pm)',
        ),
        (
            expected_outbound_content,
            'yesterday at midnight',
        ),
        (
            expected_outbound_content,
            'yesterday at midnight',
        ),
        (
            expected_outbound_content,
            'yesterday at midnight',
        ),
        (
            expected_outbound_content,
            'yesterday at midnight',
        ),
        (
            expected_outbound_content,
            'yesterday at midnight',
        ),
    ]):
        assert (
            normalize_spaces(messages[index].text),
            normalize_spaces(statuses[index].text),
        ) == expected

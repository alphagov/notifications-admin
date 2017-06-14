import pytest
from bs4 import BeautifulSoup

from flask import (
    url_for,
)
from notifications_python_client.errors import HTTPError
from tests.conftest import (
    SERVICE_ONE_ID,
)
from tests.app.test_utils import normalize_spaces
from freezegun import freeze_time
from unittest import mock
from app.main.views.conversation import get_user_number


@mock.patch(
    'app.main.views.conversation.service_api_client.get_inbound_sms_by_id',
    return_value={
        'user_number': '4407900900123'
    }
)
@mock.patch(
    'app.main.views.conversation.notification_api_client.get_notification',
    side_effect=HTTPError,
)
def test_get_user_phone_number_when_only_inbound_exists(
    mock_get_notification,
    mock_get_inbound_sms,
):
    assert get_user_number('service', 'notification') == '07900 900123'
    mock_get_inbound_sms.assert_called_once_with('service', 'notification')
    assert mock_get_notification.called is False


@mock.patch(
    'app.main.views.conversation.service_api_client.get_inbound_sms_by_id',
    side_effect=HTTPError,
)
@mock.patch(
    'app.main.views.conversation.notification_api_client.get_notification',
    return_value={
        'to': '15550000000'
    }
)
def test_get_user_phone_number_when_only_outbound_exists(
    mock_get_notification,
    mock_get_inbound_sms,
):
    assert get_user_number('service', 'notification') == '+1 555-000-0000'
    mock_get_inbound_sms.assert_called_once_with('service', 'notification')
    mock_get_notification.assert_called_once_with('service', 'notification')


@mock.patch(
    'app.main.views.conversation.service_api_client.get_inbound_sms_by_id',
    side_effect=HTTPError,
)
@mock.patch(
    'app.main.views.conversation.notification_api_client.get_notification',
    side_effect=HTTPError,
)
def test_get_user_phone_number_raises_if_both_API_requests_fail(
    mock_get_notification,
    mock_get_inbound_sms,
):
    with pytest.raises(HTTPError):
        get_user_number('service', 'notification')
    mock_get_inbound_sms.assert_called_once_with('service', 'notification')
    mock_get_notification.assert_called_once_with('service', 'notification')


@pytest.mark.parametrize('index, expected', enumerate([
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
        'template content',
        'yesterday at midnight',
    ),
    (
        'template content',
        'yesterday at midnight',
    ),
    (
        'template content',
        'yesterday at midnight',
    ),
    (
        'template content',
        'yesterday at midnight',
    ),
    (
        'template content',
        'yesterday at midnight',
    ),
]))
@freeze_time("2012-01-01 00:00:00")
def test_view_conversation(
    logged_in_client,
    fake_uuid,
    mock_get_notification,
    mock_get_inbound_sms,
    mock_get_notifications,
    index,
    expected,
):

    response = logged_in_client.get(url_for(
        'main.conversation',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    messages = page.select('.sms-message-wrapper')
    statuses = page.select('.sms-message-status')

    assert len(messages) == 13
    assert len(statuses) == 13
    assert (
        normalize_spaces(messages[index].text),
        normalize_spaces(statuses[index].text),
    ) == expected

import pytest
from bs4 import BeautifulSoup

from flask import (
    url_for,
)
from tests.conftest import (
    SERVICE_ONE_ID,
)
from tests.app.test_utils import normalize_spaces
from freezegun import freeze_time


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

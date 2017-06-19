from freezegun import freeze_time
import pytest

from app.utils import (
    REQUESTED_STATUSES,
    FAILURE_STATUSES,
    SENDING_STATUSES,
    DELIVERED_STATUSES,
)

from tests.app.test_utils import normalize_spaces
from tests.conftest import mock_get_notification


@pytest.mark.parametrize('notification_status, expected_status', [
    ('created', 'Sending'),
    ('sending', 'Sending'),
    ('delivered', 'Delivered'),
    ('failed', 'Failed'),
    ('temporary-failure', 'Phone not accepting messages right now'),
    ('permanent-failure', 'Phone number doesn’t exist'),
    ('technical-failure', 'Technical failure'),
])
@freeze_time("2016-01-01 11:09:00.061258")
def test_notification_status_page_shows_details(
    client_request,
    mocker,
    service_one,
    fake_uuid,
    notification_status,
    expected_status,
):

    _mock_get_notification = mock_get_notification(
        mocker,
        fake_uuid,
        notification_status=notification_status
    )

    page = client_request.get(
        'main.view_notification',
        service_id=service_one['id'],
        notification_id=fake_uuid
    )

    assert normalize_spaces(page.select('.sms-message-wrapper')[0].text) == (
        'service one: hello Jo'
    )
    assert normalize_spaces(page.select('.ajax-block-container p')[0].text) == (
        expected_status
    )

    _mock_get_notification.assert_called_with(
        service_one['id'],
        fake_uuid
    )

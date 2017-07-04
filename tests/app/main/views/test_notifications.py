from freezegun import freeze_time
import pytest

from app.utils import (
    REQUESTED_STATUSES,
    FAILURE_STATUSES,
    SENDING_STATUSES,
    DELIVERED_STATUSES,
)

from tests.app.test_utils import normalize_spaces
from tests.conftest import mock_get_notification, SERVICE_ONE_ID


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

    assert normalize_spaces(page.select('.sms-message-recipient')[0].text) == (
        'To: 07123456789'
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


@pytest.mark.parametrize('template_redaction_setting, expected_content', [
    (False, 'service one: hello Jo'),
    (True, 'service one: hello hidden'),
])
@freeze_time("2016-01-01 11:09:00.061258")
def test_notification_status_page_respects_redaction(
    client_request,
    mocker,
    service_one,
    fake_uuid,
    template_redaction_setting,
    expected_content,
):

    _mock_get_notification = mock_get_notification(
        mocker,
        fake_uuid,
        redact_personalisation=template_redaction_setting,
    )

    page = client_request.get(
        'main.view_notification',
        service_id=service_one['id'],
        notification_id=fake_uuid
    )

    assert normalize_spaces(page.select('.sms-message-wrapper')[0].text) == expected_content

    _mock_get_notification.assert_called_with(
        service_one['id'],
        fake_uuid,
    )


@freeze_time("2012-01-01 01:01")
def test_notification_page_doesnt_link_to_template_in_tour(
    client_request,
    fake_uuid,
    mock_get_notification,
):

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        help=3,
    )

    assert normalize_spaces(page.select('main p:nth-of-type(1)')[0].text) == (
        'sample template sent by Test User on 1 January at 1:01am'
    )
    assert len(page.select('main p:nth-of-type(1) a')) == 0

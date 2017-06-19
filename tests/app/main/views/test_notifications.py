from freezegun import freeze_time
import pytest
from werkzeug.datastructures import MultiDict

from app.main.views.notifications import get_status_arg
from app.utils import (
    REQUESTED_STATUSES,
    FAILURE_STATUSES,
    SENDING_STATUSES,
    DELIVERED_STATUSES,
)

from tests.conftest import mock_get_notification


@freeze_time("2016-01-01 11:09:00.061258")
def test_notification_status_page_shows_details(
    client_request,
    mock_get_notification,
    service_one,
    fake_uuid,
):
    page = client_request.get(
        'main.view_notification',
        service_id=service_one['id'],
        notification_id=fake_uuid
    )

    assert page.find('div', {'class': 'sms-message-wrapper'}).text.strip() == 'service one: template content'
    assert ' '.join(page.find('tbody').find('tr').text.split()) == '07123456789 Delivered 1 January at 11:10am'

    mock_get_notification.assert_called_with(
        service_one['id'],
        fake_uuid
    )

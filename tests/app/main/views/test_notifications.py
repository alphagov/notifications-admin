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


@pytest.mark.parametrize('multidict_args, expected_statuses', [
    ([], REQUESTED_STATUSES),
    ([('status', '')], REQUESTED_STATUSES),
    ([('status', 'garbage')], REQUESTED_STATUSES),
    ([('status', 'sending')], SENDING_STATUSES),
    ([('status', 'delivered')], DELIVERED_STATUSES),
    ([('status', 'failed')], FAILURE_STATUSES),
])
def test_status_filters(mocker, multidict_args, expected_statuses):
    mocker.patch('app.main.views.notifications.current_app')

    args = MultiDict(multidict_args)
    args['status'] = get_status_arg(args)

    assert sorted(args['status']) == sorted(expected_statuses)


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


@pytest.mark.parametrize('notification_status, expected_big_number_vals', [
    ('created', [1, 1, 0, 0]),
    ('sending', [1, 1, 0, 0]),
    ('delivered', [1, 0, 1, 0]),
    ('temporary-failure', [1, 0, 0, 1]),
])
def test_notification_status_page_shows_correct_numbers(
    client_request,
    mocker,
    service_one,
    fake_uuid,
    notification_status,
    expected_big_number_vals
):
    mock_get_notification(mocker, fake_uuid, notification_status=notification_status)

    page = client_request.get(
        'main.view_notification',
        service_id=service_one['id'],
        notification_id=fake_uuid
    )

    big_numbers = page.find_all('div', {'class': 'big-number-number'})
    assert expected_big_number_vals == [int(num.text.strip()) for num in big_numbers]

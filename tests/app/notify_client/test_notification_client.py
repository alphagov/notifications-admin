import pytest
from app.notify_client.notification_api_client import NotificationApiClient


def test_client_gets_notifications(mocker):

    mock_get = mocker.patch('app.notify_client.notification_api_client.NotificationApiClient.get')
    NotificationApiClient().get_all_notifications()
    mock_get.assert_called_once_with(url='/notifications', params={})


def test_client_gets_notifications_with_page(mocker):

    mock_get = mocker.patch('app.notify_client.notification_api_client.NotificationApiClient.get')
    NotificationApiClient().get_all_notifications(page=99)
    mock_get.assert_called_once_with(url='/notifications', params={'page': 99})


@pytest.mark.parametrize("arguments,expected_call", [
    (
        {},
        {'url': '/service/abcd1234/notifications', 'params': {}}
    ),
    (
        {'page': 99},
        {'url': '/service/abcd1234/notifications', 'params': {'page': 99}}
    ),
    (
        {'include_jobs': False},
        {'url': '/service/abcd1234/notifications', 'params': {'include_jobs': False}}
    ),
    (
        {'include_from_test_key': True},
        {'url': '/service/abcd1234/notifications', 'params': {'include_from_test_key': True}}
    ),
    (
        {'job_id': 'efgh5678'},
        {'url': '/service/abcd1234/job/efgh5678/notifications', 'params': {}}
    ),
    (
        {'job_id': 'efgh5678', 'page': 48},
        {'url': '/service/abcd1234/job/efgh5678/notifications', 'params': {'page': 48}}
    )
])
def test_client_gets_notifications_for_service_and_job_by_page(mocker, arguments, expected_call):

    mock_get = mocker.patch('app.notify_client.notification_api_client.NotificationApiClient.get')
    NotificationApiClient().get_notifications_for_service('abcd1234', **arguments)
    mock_get.assert_called_once_with(**expected_call)

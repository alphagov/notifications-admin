import uuid

import pytest

from app.notify_client.notification_api_client import NotificationApiClient
from tests import notification_json, single_notification_json


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


def test_send_notification(mocker, logged_in_client, active_user_with_permissions):
    mock_post = mocker.patch('app.notify_client.notification_api_client.NotificationApiClient.post')
    NotificationApiClient().send_notification(
        'foo',
        template_id='bar',
        recipient='07700900001',
        personalisation=None,
        sender_id=None
    )
    mock_post.assert_called_once_with(
        url='/service/foo/send-notification',
        data={
            'template_id': 'bar',
            'to': '07700900001',
            'personalisation': None,
            'created_by': active_user_with_permissions['id']
        }
    )


def test_get_notification(mocker):
    mock_get = mocker.patch('app.notify_client.notification_api_client.NotificationApiClient.get')
    NotificationApiClient().get_notification('foo', 'bar')
    mock_get.assert_called_once_with(
        url='/service/foo/notifications/bar'
    )


@pytest.mark.parametrize("letter_status, expected_status", [
    ('created', 'accepted'),
    ('sending', 'accepted'),
    ('delivered', 'received'),
    ('returned-letter', 'received'),
    ("technical-failure", "technical-failure")
])
def test_get_api_notifications_changes_letter_statuses(mocker, letter_status, expected_status):
    service_id = str(uuid.uuid4())
    sms_notification = single_notification_json(service_id, notification_type='sms', status='created')
    email_notification = single_notification_json(service_id, notification_type='email', status='created')
    letter_notification = single_notification_json(service_id, notification_type='letter', status=letter_status)
    notis = notification_json(service_id=service_id, rows=0)
    notis['notifications'] = [sms_notification, email_notification, letter_notification]

    mocker.patch('app.notify_client.notification_api_client.NotificationApiClient.get', return_value=notis)

    ret = NotificationApiClient().get_api_notifications_for_service(service_id)

    assert ret['notifications'][0]['notification_type'] == 'sms'
    assert ret['notifications'][1]['notification_type'] == 'email'
    assert ret['notifications'][2]['notification_type'] == 'letter'
    assert ret['notifications'][0]['status'] == 'created'
    assert ret['notifications'][1]['status'] == 'created'
    assert ret['notifications'][2]['status'] == expected_status


def test_update_notification_to_cancelled(mocker):
    mock_post = mocker.patch('app.notify_client.notification_api_client.NotificationApiClient.post')
    NotificationApiClient().update_notification_to_cancelled('foo', 'bar')
    mock_post.assert_called_once_with(
        url='/service/foo/notifications/bar/cancel',
        data={},
    )

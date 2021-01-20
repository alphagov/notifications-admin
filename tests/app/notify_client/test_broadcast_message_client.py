from app.notify_client.broadcast_message_api_client import (
    BroadcastMessageAPIClient,
)


def test_create_broadcast_message(mocker):
    client = BroadcastMessageAPIClient()
    mocker.patch('app.notify_client.current_user', id='1')
    mock_post = mocker.patch(
        'app.notify_client.broadcast_message_api_client.BroadcastMessageAPIClient.post'
    )
    client.create_broadcast_message(
        service_id='12345',
        template_id='67890',
        content=None,
        reference=None,
    )
    mock_post.assert_called_once_with(
        '/service/12345/broadcast-message',
        data={
            'service_id': '12345',
            'template_id': '67890',
            'personalisation': {},
            'created_by': '1',
        },
    )


def test_get_broadcast_messages(mocker):
    client = BroadcastMessageAPIClient()
    mock_get = mocker.patch(
        'app.notify_client.broadcast_message_api_client.BroadcastMessageAPIClient.get'
    )
    client.get_broadcast_messages('12345')
    mock_get.assert_called_once_with(
        '/service/12345/broadcast-message',
    )


def test_get_broadcast_message(mocker):
    client = BroadcastMessageAPIClient()
    mocker.patch('app.notify_client.current_user', id='1')
    mock_get = mocker.patch(
        'app.notify_client.broadcast_message_api_client.BroadcastMessageAPIClient.get',
        return_value={'abc': 'def'},
    )
    mock_redis_set = mocker.patch('app.extensions.RedisClient.set')
    client.get_broadcast_message(service_id='12345', broadcast_message_id='67890')
    mock_get.assert_called_once_with(
        '/service/12345/broadcast-message/67890',
    )
    mock_redis_set.assert_called_once_with(
        'service-12345-broadcast-message-67890',
        '{"abc": "def"}',
        ex=604_800,
    )


def test_update_broadcast_message(mocker):
    client = BroadcastMessageAPIClient()
    mocker.patch('app.notify_client.current_user', id='1')
    mock_post = mocker.patch(
        'app.notify_client.broadcast_message_api_client.BroadcastMessageAPIClient.post'
    )
    mock_redis_delete = mocker.patch('app.extensions.RedisClient.delete')
    client.update_broadcast_message(
        service_id='12345',
        broadcast_message_id='67890',
        data={'abc': 'def'},
    )
    mock_post.assert_called_once_with(
        '/service/12345/broadcast-message/67890',
        data={'abc': 'def'},
    )
    mock_redis_delete.assert_called_once_with('service-12345-broadcast-message-67890')


def test_update_broadcast_message_status(mocker):
    client = BroadcastMessageAPIClient()
    mocker.patch('app.notify_client.current_user', id='1')
    mock_post = mocker.patch(
        'app.notify_client.broadcast_message_api_client.BroadcastMessageAPIClient.post'
    )
    mock_redis_delete = mocker.patch('app.extensions.RedisClient.delete')
    client.update_broadcast_message_status(
        'cancelled',
        service_id='12345',
        broadcast_message_id='67890',
    )
    mock_post.assert_called_once_with(
        '/service/12345/broadcast-message/67890/status',
        data={'created_by': '1', 'status': 'cancelled'},
    )
    mock_redis_delete.assert_called_once_with('service-12345-broadcast-message-67890')

from unittest.mock import ANY
import json

from app.notify_client.api_key_api_client import ApiKeyApiClient
from tests.conftest import SERVICE_ONE_ID


def test_revoke_key_hits_api_and_deletes_redis(logged_in_client, mocker):
    api_key_id = 'my api key id'
    mock_redis_delete = mocker.patch('app.notify_client.cache.redis_client.delete')
    mock_post = mocker.patch('app.notify_client.api_key_api_client.ApiKeyApiClient.post')

    client = ApiKeyApiClient()

    client.revoke_api_key(SERVICE_ONE_ID, api_key_id)

    mock_post.assert_called_once_with(url=f'/service/{SERVICE_ONE_ID}/api-key/revoke/{api_key_id}', data=ANY)
    mock_redis_delete.assert_called_once_with(f'service-{SERVICE_ONE_ID}-api-keys')


def test_get_api_keys_gets_and_sets_cache(logged_in_client, mocker):
    mock_redis_get = mocker.patch('app.notify_client.cache.redis_client.get', return_value=None)
    mock_redis_set = mocker.patch('app.notify_client.cache.redis_client.set')
    mock_get = mocker.patch('app.notify_client.api_key_api_client.ApiKeyApiClient.get', return_value=[{'foo': 'bar'}])

    client = ApiKeyApiClient()

    ret = client.get_api_keys(SERVICE_ONE_ID)
    assert ret == mock_get.return_value

    mock_redis_get.assert_called_once_with(f'service-{SERVICE_ONE_ID}-api-keys')
    mock_redis_set.assert_called_once_with(f'service-{SERVICE_ONE_ID}-api-keys', json.dumps(ret), ex=ANY)


def test_create_api_key_deletes_cache(logged_in_client, mocker):
    mock_redis_delete = mocker.patch('app.notify_client.cache.redis_client.delete')
    mock_post = mocker.patch('app.notify_client.api_key_api_client.ApiKeyApiClient.post')

    client = ApiKeyApiClient()

    client.create_api_key(SERVICE_ONE_ID, 'key name', 'key type')

    mock_post.assert_called_once_with(url=f'/service/{SERVICE_ONE_ID}/api-key', data=ANY)
    mock_redis_delete.assert_called_once_with(f'service-{SERVICE_ONE_ID}-api-keys')

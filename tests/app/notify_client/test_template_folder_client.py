import uuid
from unittest.mock import call

import pytest
from orderedset import OrderedSet

from app.notify_client.template_folder_api_client import TemplateFolderAPIClient


@pytest.mark.parametrize('parent_id', [uuid.uuid4(), None])
def test_create_template_folder_calls_correct_api_endpoint(mocker, parent_id):
    mock_redis_delete = mocker.patch('app.extensions.RedisClient.delete')

    some_service_id = uuid.uuid4()
    expected_url = '/service/{}/template-folder'.format(some_service_id)
    data = {'name': 'foo', 'parent_id': parent_id}

    client = TemplateFolderAPIClient()

    mock_post = mocker.patch('app.notify_client.template_folder_api_client.TemplateFolderAPIClient.post')

    client.create_template_folder(some_service_id, name='foo', parent_id=parent_id)

    mock_post.assert_called_once_with(expected_url, data)
    mock_redis_delete.assert_called_once_with('service-{}-template-folders'.format(some_service_id))


def test_get_template_folders_calls_correct_api_endpoint(mocker):
    mock_redis_get = mocker.patch('app.extensions.RedisClient.get', return_value=None)
    mock_redis_set = mocker.patch('app.extensions.RedisClient.set')
    mock_api_get = mocker.patch(
        'app.notify_client.NotifyAdminAPIClient.get',
        return_value={'template_folders': {'a': 'b'}}
    )

    some_service_id = uuid.uuid4()
    expected_url = '/service/{}/template-folder'.format(some_service_id)
    redis_key = 'service-{}-template-folders'.format(some_service_id)

    client = TemplateFolderAPIClient()

    ret = client.get_template_folders(some_service_id)

    assert ret == {'a': 'b'}

    mock_redis_get.assert_called_once_with(redis_key)
    mock_api_get.assert_called_once_with(expected_url)
    mock_redis_set.assert_called_once_with(redis_key, '{"a": "b"}', ex=604800)


def test_move_templates_and_folders(mocker):

    mock_redis_delete = mocker.patch('app.extensions.RedisClient.delete')
    mock_api_post = mocker.patch('app.notify_client.NotifyAdminAPIClient.post')

    some_service_id = uuid.uuid4()
    some_folder_id = uuid.uuid4()

    TemplateFolderAPIClient().move_to_folder(
        some_service_id,
        some_folder_id,
        template_ids=OrderedSet(('a', 'b', 'c')),
        folder_ids=OrderedSet(('1', '2', '3')),
    )

    mock_api_post.assert_called_once_with(
        '/service/{}/template-folder/{}/contents'.format(
            some_service_id, some_folder_id
        ),
        {
            'folders': ['1', '2', '3'],
            'templates': ['a', 'b', 'c'],
        },
    )
    assert mock_redis_delete.call_args_list == [
        call(
            f'service-{some_service_id}-template-a-version-None',
            f'service-{some_service_id}-template-b-version-None',
            f'service-{some_service_id}-template-c-version-None',
        ),
        call('service-{}-templates'.format(some_service_id)),
        call('service-{}-template-folders'.format(some_service_id)),
    ]


def test_move_templates_and_folders_to_root(mocker):

    mock_api_post = mocker.patch('app.notify_client.NotifyAdminAPIClient.post')

    some_service_id = uuid.uuid4()

    TemplateFolderAPIClient().move_to_folder(
        some_service_id,
        None,
        template_ids=OrderedSet(('a', 'b', 'c')),
        folder_ids=OrderedSet(('1', '2', '3')),
    )

    mock_api_post.assert_called_once_with(
        '/service/{}/template-folder/contents'.format(some_service_id),
        {
            'folders': ['1', '2', '3'],
            'templates': ['a', 'b', 'c'],
        },
    )


def test_update_template_folder_calls_correct_api_endpoint(mocker):
    mock_redis_delete = mocker.patch('app.extensions.RedisClient.delete')

    some_service_id = uuid.uuid4()
    template_folder_id = uuid.uuid4()
    expected_url = '/service/{}/template-folder/{}'.format(some_service_id, template_folder_id)
    data = {'name': 'foo', 'users_with_permission': ['some_id']}

    client = TemplateFolderAPIClient()

    mock_post = mocker.patch('app.notify_client.template_folder_api_client.TemplateFolderAPIClient.post')

    client.update_template_folder(some_service_id, template_folder_id, name='foo', users_with_permission=['some_id'])

    mock_post.assert_called_once_with(expected_url, data)
    mock_redis_delete.assert_called_once_with('service-{}-template-folders'.format(some_service_id))


def test_delete_template_folder_calls_correct_api_endpoint(mocker):
    mock_redis_delete = mocker.patch('app.extensions.RedisClient.delete')

    some_service_id = uuid.uuid4()
    template_folder_id = uuid.uuid4()
    expected_url = '/service/{}/template-folder/{}'.format(some_service_id, template_folder_id)

    client = TemplateFolderAPIClient()

    mock_delete = mocker.patch('app.notify_client.template_folder_api_client.TemplateFolderAPIClient.delete')

    client.delete_template_folder(some_service_id, template_folder_id)

    mock_delete.assert_called_once_with(expected_url, {})
    mock_redis_delete.assert_called_once_with('service-{}-template-folders'.format(some_service_id))

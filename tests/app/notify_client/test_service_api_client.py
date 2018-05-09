from unittest.mock import call

import pytest

from app import invite_api_client, service_api_client, user_api_client
from app.notify_client.service_api_client import ServiceAPIClient
from tests.conftest import SERVICE_ONE_ID, fake_uuid

FAKE_TEMPLATE_ID = fake_uuid()


def test_client_posts_archived_true_when_deleting_template(mocker):
    service_id = fake_uuid()
    template_id = fake_uuid()
    mocker.patch('app.notify_client.current_user', id='1')

    expected_data = {
        'archived': True,
        'created_by': '1'
    }
    expected_url = '/service/{}/template/{}'.format(service_id, template_id)

    client = ServiceAPIClient()
    mock_post = mocker.patch('app.notify_client.service_api_client.ServiceAPIClient.post')

    client.delete_service_template(service_id, template_id)
    mock_post.assert_called_once_with(expected_url, data=expected_data)


def test_client_gets_service(mocker):
    client = ServiceAPIClient()
    mock_get = mocker.patch.object(client, 'get', return_value={})

    client.get_service('foo')
    mock_get.assert_called_once_with('/service/foo')


@pytest.mark.parametrize('today_only', [True, False])
def test_client_gets_service_statistics(mocker, today_only):
    client = ServiceAPIClient()
    mock_get = mocker.patch.object(client, 'get', return_value={'data': {'a': 'b'}})

    ret = client.get_service_statistics('foo', today_only)

    assert ret == {'a': 'b'}
    mock_get.assert_called_once_with('/service/foo/statistics', params={'today_only': today_only})


def test_client_only_updates_allowed_attributes(mocker):
    mocker.patch('app.notify_client.current_user', id='1')
    with pytest.raises(TypeError) as error:
        ServiceAPIClient().update_service('service_id', foo='bar')
    assert str(error.value) == 'Not allowed to update service attributes: foo'


def test_client_creates_service_with_correct_data(
    mocker,
    active_user_with_permissions,
    fake_uuid,
):
    client = ServiceAPIClient()
    mock_post = mocker.patch.object(client, 'post', return_value={'data': {'id': None}})
    mocker.patch('app.notify_client.current_user', id='123')

    client.create_service(
        'My first service',
        'central_government',
        1,
        True,
        fake_uuid,
        'test@example.com',
    )
    mock_post.assert_called_once_with(
        '/service',
        dict(
            # Autogenerated arguments
            created_by='123',
            active=True,
            # ‘service_name’ argument is coerced to ‘name’
            name='My first service',
            # The rest pass through with the same names
            organisation_type='central_government',
            message_limit=1,
            restricted=True,
            user_id=fake_uuid,
            email_from='test@example.com',
        ),
    )


@pytest.mark.parametrize('template_data, extra_args, expected_count', (
    (
        [],
        {},
        0,
    ),
    (
        [],
        {'template_type': 'email'},
        0,
    ),
    (
        [
            {'template_type': 'email'},
            {'template_type': 'sms'},
        ],
        {},
        2,
    ),
    (
        [
            {'template_type': 'email'},
            {'template_type': 'sms'},
        ],
        {'template_type': 'email'},
        1,
    ),
    (
        [
            {'template_type': 'email'},
            {'template_type': 'sms'},
        ],
        {'template_type': 'letter'},
        0,
    ),
))
def test_client_returns_count_of_service_templates(
    app_,
    mocker,
    template_data,
    extra_args,
    expected_count,
):

    mocker.patch(
        'app.service_api_client.get_service_templates',
        return_value={'data': template_data}
    )

    assert service_api_client.count_service_templates(
        SERVICE_ONE_ID, **extra_args
    ) == expected_count


@pytest.mark.parametrize(
    (
        'client_method,'
        'extra_args,'
        'expected_cache_get_calls,'
        'cache_value,'
        'expected_api_calls,'
        'expected_cache_set_calls,'
        'expected_return_value,'
    ),
    [
        (
            service_api_client.get_service,
            [SERVICE_ONE_ID],
            [
                call('service-{}'.format(SERVICE_ONE_ID))
            ],
            b'{"data_from": "cache"}',
            [],
            [],
            {'data_from': 'cache'},
        ),
        (
            service_api_client.get_service,
            [SERVICE_ONE_ID],
            [
                call('service-{}'.format(SERVICE_ONE_ID))
            ],
            None,
            [
                call('/service/{}'.format(SERVICE_ONE_ID))
            ],
            [
                call(
                    'service-{}'.format(SERVICE_ONE_ID),
                    '{"data_from": "api"}',
                    ex=604800,
                )
            ],
            {'data_from': 'api'},
        ),
        (
            service_api_client.get_service_template,
            [SERVICE_ONE_ID, FAKE_TEMPLATE_ID],
            [
                call('template-{}-version-None'.format(FAKE_TEMPLATE_ID))
            ],
            b'{"data_from": "cache"}',
            [],
            [],
            {'data_from': 'cache'},
        ),
        (
            service_api_client.get_service_template,
            [SERVICE_ONE_ID, FAKE_TEMPLATE_ID],
            [
                call('template-{}-version-None'.format(FAKE_TEMPLATE_ID))
            ],
            None,
            [
                call('/service/{}/template/{}'.format(SERVICE_ONE_ID, FAKE_TEMPLATE_ID))
            ],
            [
                call(
                    'template-{}-version-None'.format(FAKE_TEMPLATE_ID),
                    '{"data_from": "api"}',
                    ex=604800,
                )
            ],
            {'data_from': 'api'},
        ),
        (
            service_api_client.get_service_template,
            [SERVICE_ONE_ID, FAKE_TEMPLATE_ID, 1],
            [
                call('template-{}-version-1'.format(FAKE_TEMPLATE_ID))
            ],
            b'{"data_from": "cache"}',
            [],
            [],
            {'data_from': 'cache'},
        ),
        (
            service_api_client.get_service_template,
            [SERVICE_ONE_ID, FAKE_TEMPLATE_ID, 1],
            [
                call('template-{}-version-1'.format(FAKE_TEMPLATE_ID))
            ],
            None,
            [
                call('/service/{}/template/{}/version/1'.format(SERVICE_ONE_ID, FAKE_TEMPLATE_ID))
            ],
            [
                call(
                    'template-{}-version-1'.format(FAKE_TEMPLATE_ID),
                    '{"data_from": "api"}',
                    ex=604800,
                )
            ],
            {'data_from': 'api'},
        ),
        (
            service_api_client.get_service_templates,
            [SERVICE_ONE_ID],
            [
                call('service-{}-templates'.format(SERVICE_ONE_ID))
            ],
            b'{"data_from": "cache"}',
            [],
            [],
            {'data_from': 'cache'},
        ),
        (
            service_api_client.get_service_templates,
            [SERVICE_ONE_ID],
            [
                call('service-{}-templates'.format(SERVICE_ONE_ID))
            ],
            None,
            [
                call('/service/{}/template'.format(SERVICE_ONE_ID))
            ],
            [
                call(
                    'service-{}-templates'.format(SERVICE_ONE_ID),
                    '{"data_from": "api"}',
                    ex=604800,
                )
            ],
            {'data_from': 'api'},
        ),
        (
            service_api_client.get_service_template_versions,
            [SERVICE_ONE_ID, FAKE_TEMPLATE_ID],
            [
                call('template-{}-versions'.format(FAKE_TEMPLATE_ID))
            ],
            b'{"data_from": "cache"}',
            [],
            [],
            {'data_from': 'cache'},
        ),
        (
            service_api_client.get_service_template_versions,
            [SERVICE_ONE_ID, FAKE_TEMPLATE_ID],
            [
                call('template-{}-versions'.format(FAKE_TEMPLATE_ID))
            ],
            None,
            [
                call('/service/{}/template/{}/versions'.format(SERVICE_ONE_ID, FAKE_TEMPLATE_ID))
            ],
            [
                call(
                    'template-{}-versions'.format(FAKE_TEMPLATE_ID),
                    '{"data_from": "api"}',
                    ex=604800,
                )
            ],
            {'data_from': 'api'},
        ),
    ]
)
def test_returns_value_from_cache(
    mocker,
    client_method,
    extra_args,
    expected_cache_get_calls,
    cache_value,
    expected_return_value,
    expected_api_calls,
    expected_cache_set_calls,
):

    mock_redis_get = mocker.patch(
        'app.notify_client.RedisClient.get',
        return_value=cache_value,
    )
    mock_api_get = mocker.patch(
        'app.notify_client.NotifyAdminAPIClient.get',
        return_value={'data_from': 'api'},
    )
    mock_redis_set = mocker.patch(
        'app.notify_client.RedisClient.set',
    )

    assert client_method(*extra_args) == expected_return_value

    assert mock_redis_get.call_args_list == expected_cache_get_calls
    assert mock_api_get.call_args_list == expected_api_calls
    assert mock_redis_set.call_args_list == expected_cache_set_calls


@pytest.mark.parametrize('client, method, extra_args, extra_kwargs', [
    (service_api_client, 'update_service', [SERVICE_ONE_ID], {'name': 'foo'}),
    (service_api_client, 'update_service_with_properties', [SERVICE_ONE_ID], {'properties': {}}),
    (service_api_client, 'archive_service', [SERVICE_ONE_ID], {}),
    (service_api_client, 'suspend_service', [SERVICE_ONE_ID], {}),
    (service_api_client, 'resume_service', [SERVICE_ONE_ID], {}),
    (service_api_client, 'remove_user_from_service', [SERVICE_ONE_ID, ''], {}),
    (service_api_client, 'update_whitelist', [SERVICE_ONE_ID, {}], {}),
    (service_api_client, 'create_service_inbound_api', [SERVICE_ONE_ID] + [''] * 3, {}),
    (service_api_client, 'update_service_inbound_api', [SERVICE_ONE_ID] + [''] * 4, {}),
    (service_api_client, 'add_reply_to_email_address', [SERVICE_ONE_ID, ''], {}),
    (service_api_client, 'update_reply_to_email_address', [SERVICE_ONE_ID] + [''] * 2, {}),
    (service_api_client, 'delete_reply_to_email_address', [SERVICE_ONE_ID, ''], {}),
    (service_api_client, 'add_letter_contact', [SERVICE_ONE_ID, ''], {}),
    (service_api_client, 'update_letter_contact', [SERVICE_ONE_ID] + [''] * 2, {}),
    (service_api_client, 'add_sms_sender', [SERVICE_ONE_ID, ''], {}),
    (service_api_client, 'update_sms_sender', [SERVICE_ONE_ID] + [''] * 2, {}),
    (service_api_client, 'delete_sms_sender', [SERVICE_ONE_ID, ''], {}),
    (service_api_client, 'update_service_callback_api', [SERVICE_ONE_ID] + [''] * 4, {}),
    (service_api_client, 'create_service_callback_api', [SERVICE_ONE_ID] + [''] * 3, {}),
    (user_api_client, 'add_user_to_service', [SERVICE_ONE_ID, fake_uuid(), []], {}),
    (invite_api_client, 'accept_invite', [SERVICE_ONE_ID, fake_uuid()], {}),
])
def test_deletes_service_cache(
    app_,
    mock_get_user,
    mocker,
    client,
    method,
    extra_args,
    extra_kwargs,
):
    mocker.patch('app.notify_client.current_user', id='1')
    mock_redis_delete = mocker.patch('app.notify_client.RedisClient.delete')
    mock_request = mocker.patch('notifications_python_client.base.BaseAPIClient.request')

    getattr(client, method)(*extra_args, **extra_kwargs)

    assert call('service-{}'.format(SERVICE_ONE_ID)) in mock_redis_delete.call_args_list
    assert len(mock_request.call_args_list) == 1


@pytest.mark.parametrize('method, extra_args, expected_cache_deletes', [
    ('create_service_template', ['name', 'type_', 'content', SERVICE_ONE_ID], [
        'service-{}-templates'.format(SERVICE_ONE_ID),
    ]),
    ('update_service_template', [FAKE_TEMPLATE_ID, 'foo', 'sms', 'bar', SERVICE_ONE_ID], [
        'service-{}-templates'.format(SERVICE_ONE_ID),
        'template-{}-version-None'.format(FAKE_TEMPLATE_ID),
        'template-{}-versions'.format(FAKE_TEMPLATE_ID),
    ]),
    ('redact_service_template', [SERVICE_ONE_ID, FAKE_TEMPLATE_ID], [
        'service-{}-templates'.format(SERVICE_ONE_ID),
        'template-{}-version-None'.format(FAKE_TEMPLATE_ID),
        'template-{}-versions'.format(FAKE_TEMPLATE_ID),
    ]),
    ('update_service_template_sender', [SERVICE_ONE_ID, FAKE_TEMPLATE_ID, 'foo'], [
        'service-{}-templates'.format(SERVICE_ONE_ID),
        'template-{}-version-None'.format(FAKE_TEMPLATE_ID),
        'template-{}-versions'.format(FAKE_TEMPLATE_ID),
    ]),
    ('delete_service_template', [SERVICE_ONE_ID, FAKE_TEMPLATE_ID], [
        'service-{}-templates'.format(SERVICE_ONE_ID),
        'template-{}-version-None'.format(FAKE_TEMPLATE_ID),
        'template-{}-versions'.format(FAKE_TEMPLATE_ID),
    ]),
])
def test_deletes_caches_when_modifying_templates(
    app_,
    mock_get_user,
    mocker,
    method,
    extra_args,
    expected_cache_deletes,
):
    mocker.patch('app.notify_client.current_user', id='1')
    mock_redis_delete = mocker.patch('app.notify_client.RedisClient.delete')
    mock_request = mocker.patch('notifications_python_client.base.BaseAPIClient.request')

    getattr(service_api_client, method)(*extra_args)

    assert mock_redis_delete.call_args_list == list(map(call, expected_cache_deletes))
    assert len(mock_request.call_args_list) == 1

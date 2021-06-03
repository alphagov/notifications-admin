import uuid
from unittest.mock import Mock, call

import pytest
from notifications_python_client.errors import HTTPError

from app import invite_api_client, service_api_client, user_api_client
from app.models.webauthn_credential import WebAuthnCredential
from tests import sample_uuid
from tests.conftest import SERVICE_ONE_ID

user_id = sample_uuid()


def test_client_gets_all_users_for_service(
    mocker,
    fake_uuid,
):

    user_api_client.max_failed_login_count = 99  # doesn't matter for this test
    mock_get = mocker.patch(
        'app.notify_client.user_api_client.UserApiClient.get',
        return_value={'data': [
            {'id': fake_uuid},
        ]}
    )

    users = user_api_client.get_users_for_service(SERVICE_ONE_ID)

    mock_get.assert_called_once_with('/service/{}/users'.format(SERVICE_ONE_ID))
    assert len(users) == 1
    assert users[0]['id'] == fake_uuid


def test_client_uses_correct_find_by_email(mocker, api_user_active):

    expected_url = '/user/email'
    expected_data = {'email': api_user_active['email_address']}

    user_api_client.max_failed_login_count = 1  # doesn't matter for this test
    mock_post = mocker.patch('app.notify_client.user_api_client.UserApiClient.post')

    user_api_client.get_user_by_email(api_user_active['email_address'])

    mock_post.assert_called_once_with(expected_url, data=expected_data)


def test_client_only_updates_allowed_attributes(mocker):
    mocker.patch('app.notify_client.current_user', id='1')
    with pytest.raises(TypeError) as error:
        user_api_client.update_user_attribute('user_id', id='1')
    assert str(error.value) == 'Not allowed to update user attributes: id'


def test_client_updates_password_separately(mocker, api_user_active):
    expected_url = '/user/{}/update-password'.format(api_user_active['id'])
    expected_params = {'_password': 'newpassword'}
    user_api_client.max_failed_login_count = 1  # doesn't matter for this test
    mock_update_password = mocker.patch('app.notify_client.user_api_client.UserApiClient.post')

    user_api_client.update_password(api_user_active['id'], expected_params['_password'])
    mock_update_password.assert_called_once_with(expected_url, data=expected_params)


def test_client_activates_if_pending(mocker, api_user_pending):
    mock_post = mocker.patch('app.notify_client.user_api_client.UserApiClient.post')
    user_api_client.max_failed_login_count = 1  # doesn't matter for this test

    user_api_client.activate_user(api_user_pending['id'])

    mock_post.assert_called_once_with('/user/{}/activate'.format(api_user_pending['id']), data=None)


def test_client_passes_admin_url_when_sending_email_auth(
    notify_admin,
    mocker,
    fake_uuid,
):
    mock_post = mocker.patch('app.notify_client.user_api_client.UserApiClient.post')

    user_api_client.send_verify_code(fake_uuid, 'email', 'ignored@example.com')

    mock_post.assert_called_once_with(
        '/user/{}/email-code'.format(fake_uuid),
        data={
            'to': 'ignored@example.com',
            'email_auth_link_host': 'http://localhost:6012',
        }
    )


def test_client_converts_admin_permissions_to_db_permissions_on_edit(notify_admin, mocker):
    mock_post = mocker.patch('app.notify_client.user_api_client.UserApiClient.post')

    user_api_client.set_user_permissions('user_id', 'service_id', permissions={'send_messages', 'view_activity'})

    assert sorted(mock_post.call_args[1]['data']['permissions'], key=lambda x: x['permission']) == sorted([
        {'permission': 'send_texts'},
        {'permission': 'send_emails'},
        {'permission': 'send_letters'},
        {'permission': 'view_activity'},
    ], key=lambda x: x['permission'])


def test_client_converts_admin_permissions_to_db_permissions_on_add_to_service(notify_admin, mocker):
    mock_post = mocker.patch('app.notify_client.user_api_client.UserApiClient.post', return_value={'data': {}})

    user_api_client.add_user_to_service('service_id',
                                        'user_id',
                                        permissions={'send_messages', 'view_activity'},
                                        folder_permissions=[])

    assert sorted(mock_post.call_args[1]['data']['permissions'], key=lambda x: x['permission']) == sorted([
        {'permission': 'send_texts'},
        {'permission': 'send_emails'},
        {'permission': 'send_letters'},
        {'permission': 'view_activity'},
    ], key=lambda x: x['permission'])


@pytest.mark.parametrize(
    (
        'expected_cache_get_calls,'
        'cache_value,'
        'expected_api_calls,'
        'expected_cache_set_calls,'
        'expected_return_value,'
    ),
    [
        (
            [
                call('user-{}'.format(user_id))
            ],
            b'{"data": "from cache"}',
            [],
            [],
            'from cache',
        ),
        (
            [
                call('user-{}'.format(user_id))
            ],
            None,
            [
                call('/user/{}'.format(user_id))
            ],
            [
                call(
                    'user-{}'.format(user_id),
                    '{"data": "from api"}',
                    ex=604800
                )
            ],
            'from api',
        ),
    ]
)
def test_returns_value_from_cache(
    notify_admin,
    mocker,
    expected_cache_get_calls,
    cache_value,
    expected_return_value,
    expected_api_calls,
    expected_cache_set_calls,
):

    mock_redis_get = mocker.patch(
        'app.extensions.RedisClient.get',
        return_value=cache_value,
    )
    mock_api_get = mocker.patch(
        'app.notify_client.NotifyAdminAPIClient.get',
        return_value={'data': 'from api'},
    )
    mock_redis_set = mocker.patch(
        'app.extensions.RedisClient.set',
    )

    user_api_client.get_user(user_id)

    assert mock_redis_get.call_args_list == expected_cache_get_calls
    assert mock_api_get.call_args_list == expected_api_calls
    assert mock_redis_set.call_args_list == expected_cache_set_calls


@pytest.mark.parametrize('client, method, extra_args, extra_kwargs', [
    (user_api_client, 'add_user_to_service', [SERVICE_ONE_ID, sample_uuid(), [], []], {}),
    (user_api_client, 'update_user_attribute', [user_id], {}),
    (user_api_client, 'reset_failed_login_count', [user_id], {}),
    (user_api_client, 'update_user_attribute', [user_id], {}),
    (user_api_client, 'update_password', [user_id, 'hunter2'], {}),
    (user_api_client, 'verify_password', [user_id, 'hunter2'], {}),
    (user_api_client, 'check_verify_code', [user_id, '', ''], {}),
    (user_api_client, 'complete_webauthn_login_attempt', [user_id], {'is_successful': True}),
    (user_api_client, 'add_user_to_service', [SERVICE_ONE_ID, user_id, [], []], {}),
    (user_api_client, 'add_user_to_organisation', [sample_uuid(), user_id], {}),
    (user_api_client, 'set_user_permissions', [user_id, SERVICE_ONE_ID, []], {}),
    (user_api_client, 'activate_user', [user_id], {}),
    (user_api_client, 'archive_user', [user_id], {}),
    (service_api_client, 'remove_user_from_service', [SERVICE_ONE_ID, user_id], {}),
    (service_api_client, 'create_service', ['', '', 0, False, user_id, sample_uuid()], {}),
    (invite_api_client, 'accept_invite', [SERVICE_ONE_ID, user_id], {}),
])
def test_deletes_user_cache(
    notify_admin,
    mock_get_user,
    mocker,
    client,
    method,
    extra_args,
    extra_kwargs,
):
    mocker.patch('app.notify_client.current_user', id='1')
    mock_redis_delete = mocker.patch('app.extensions.RedisClient.delete')
    mock_request = mocker.patch('notifications_python_client.base.BaseAPIClient.request')

    getattr(client, method)(*extra_args, **extra_kwargs)

    assert call('user-{}'.format(user_id)) in mock_redis_delete.call_args_list
    assert len(mock_request.call_args_list) == 1


def test_add_user_to_service_calls_correct_endpoint_and_deletes_keys_from_cache(mocker):
    mock_redis_delete = mocker.patch('app.extensions.RedisClient.delete')

    service_id = uuid.uuid4()
    user_id = uuid.uuid4()
    folder_id = uuid.uuid4()

    expected_url = '/service/{}/users/{}'.format(service_id, user_id)
    data = {'permissions': [], 'folder_permissions': [folder_id]}

    mock_post = mocker.patch('app.notify_client.user_api_client.UserApiClient.post')

    user_api_client.add_user_to_service(service_id, user_id, [], [folder_id])

    mock_post.assert_called_once_with(expected_url, data=data)
    assert mock_redis_delete.call_args_list == [
        call('user-{user_id}'.format(user_id=user_id)),
        call('service-{service_id}-template-folders'.format(service_id=service_id)),
        call('service-{service_id}'.format(service_id=service_id)),
    ]


def test_get_webauthn_credentials_for_user(mocker, webauthn_credential, fake_uuid):

    mock_get = mocker.patch(
        'app.notify_client.user_api_client.UserApiClient.get',
        return_value={'data': [webauthn_credential]}
    )

    credentials = user_api_client.get_webauthn_credentials_for_user(fake_uuid)

    mock_get.assert_called_once_with(f'/user/{fake_uuid}/webauthn')
    assert len(credentials) == 1
    assert credentials[0]['name'] == 'Test credential'


def test_create_webauthn_credential_for_user(mocker, webauthn_credential, fake_uuid):
    credential = WebAuthnCredential(webauthn_credential)

    mock_post = mocker.patch('app.notify_client.user_api_client.UserApiClient.post')
    expected_url = f'/user/{fake_uuid}/webauthn'

    user_api_client.create_webauthn_credential_for_user(fake_uuid, credential)
    mock_post.assert_called_once_with(expected_url, data=credential.serialize())


def test_complete_webauthn_login_attempt_returns_true_and_no_message_normally(fake_uuid, mocker):
    mock_post = mocker.patch('app.notify_client.user_api_client.UserApiClient.post')

    resp = user_api_client.complete_webauthn_login_attempt(fake_uuid, is_successful=True)

    expected_data = {'successful': True}
    mock_post.assert_called_once_with(f'/user/{fake_uuid}/complete/webauthn-login', data=expected_data)
    assert resp == (True, '')


def test_complete_webauthn_login_attempt_returns_false_and_message_on_403(fake_uuid, mocker):
    mock_post = mocker.patch(
        'app.notify_client.user_api_client.UserApiClient.post',
        side_effect=HTTPError(
            response=Mock(
                status_code=403,
                json=Mock(
                    return_value={'message': 'forbidden'}
                )
            )
        )
    )

    resp = user_api_client.complete_webauthn_login_attempt(fake_uuid, is_successful=True)

    expected_data = {'successful': True}
    mock_post.assert_called_once_with(f'/user/{fake_uuid}/complete/webauthn-login', data=expected_data)

    assert resp == (False, 'forbidden')


def test_complete_webauthn_login_attempt_raises_on_api_error(fake_uuid, mocker):
    mocker.patch(
        'app.notify_client.user_api_client.UserApiClient.post',
        side_effect=HTTPError(response=Mock(status_code=503, message='error'))
    )

    with pytest.raises(HTTPError):
        user_api_client.complete_webauthn_login_attempt(fake_uuid, is_successful=True)

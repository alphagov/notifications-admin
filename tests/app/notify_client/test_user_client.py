import pytest

from app import user_api_client


def test_client_uses_correct_find_by_email(mocker, api_user_active):

    expected_url = '/user/email'
    expected_params = {'email': api_user_active.email_address}

    user_api_client.max_failed_login_count = 1  # doesn't matter for this test
    mock_get = mocker.patch('app.notify_client.user_api_client.UserApiClient.get')

    user_api_client.get_user_by_email(api_user_active.email_address)

    mock_get.assert_called_once_with(expected_url, params=expected_params)


def test_client_only_updates_allowed_attributes(mocker):
    mocker.patch('app.notify_client.current_user', id='1')
    with pytest.raises(TypeError) as error:
        user_api_client.update_user_attribute('user_id', id='1')
    assert str(error.value) == 'Not allowed to update user attributes: id'


def test_client_updates_password_separately(mocker, api_user_active):
    expected_url = '/user/{}/update-password'.format(api_user_active.id)
    expected_params = {'_password': 'newpassword'}
    user_api_client.max_failed_login_count = 1  # doesn't matter for this test
    mock_update_password = mocker.patch('app.notify_client.user_api_client.UserApiClient.post')

    user_api_client.update_password(api_user_active.id, expected_params['_password'])
    mock_update_password.assert_called_once_with(expected_url, data=expected_params)


def test_client_activates_if_pending(mocker, api_user_pending):
    mock_post = mocker.patch('app.notify_client.user_api_client.UserApiClient.post')
    user_api_client.max_failed_login_count = 1  # doesn't matter for this test

    user_api_client.activate_user(api_user_pending)

    mock_post.assert_called_once_with('/user/{}/activate'.format(api_user_pending.id), data=None)


def test_client_doesnt_activate_if_already_active(mocker, api_user_active):
    mock_post = mocker.patch('app.notify_client.user_api_client.UserApiClient.post')

    user_api_client.activate_user(api_user_active)

    assert not mock_post.called


def test_client_passes_admin_url_when_sending_email_auth(
    app_,
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

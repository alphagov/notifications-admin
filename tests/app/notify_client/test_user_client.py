import pytest

from app.notify_client.user_api_client import UserApiClient


def test_client_uses_correct_find_by_email(mocker, api_user_active):

    expected_url = '/user/email'
    expected_params = {'email': api_user_active.email_address}

    client = UserApiClient()
    client.max_failed_login_count = 1  # doesn't matter for this test
    mock_get = mocker.patch('app.notify_client.user_api_client.UserApiClient.get')

    client.get_user_by_email(api_user_active.email_address)

    mock_get.assert_called_once_with(expected_url, params=expected_params)


def test_client_only_updates_allowed_attributes(mocker):
    mocker.patch('app.notify_client.current_user', id='1')
    with pytest.raises(TypeError) as error:
        UserApiClient().update_user_attribute('user_id', id='1')
    assert str(error.value) == 'Not allowed to update user attributes: id'


def test_client_updates_password_separately(mocker, api_user_active):
    expected_url = '/user/{}/update-password'.format(api_user_active.id)
    expected_params = {'_password': 'newpassword'}
    client = UserApiClient()
    client.max_failed_login_count = 1  # doesn't matter for this test
    mock_update_password = mocker.patch('app.notify_client.user_api_client.UserApiClient.post')

    client.update_password(api_user_active.id, expected_params['_password'])
    mock_update_password.assert_called_once_with(expected_url, data=expected_params)

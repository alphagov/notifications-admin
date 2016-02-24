from app.notify_client.user_api_client import UserApiClient


def test_client_uses_correct_find_by_email(mocker, api_user_active):

    expected_url = '/user/email'
    expected_params = {'email': api_user_active.email_address}

    client = UserApiClient()
    client.max_failed_login_count = 1  # doesn't matter for this test
    mock_get = mocker.patch('app.notify_client.user_api_client.UserApiClient.get')

    client.get_user_by_email(api_user_active.email_address)

    mock_get.assert_called_once_with(expected_url, params=expected_params)

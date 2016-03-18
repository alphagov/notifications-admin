from app.notify_client.statistics_api_client import StatisticsApiClient


def test_client_uses_correct_find_by_email(mocker, api_user_active):

    expected_url = '/service/a1b2c3d4/notifications-statistics'

    client = StatisticsApiClient()
    mock_get = mocker.patch('app.notify_client.statistics_api_client.StatisticsApiClient.get')

    client.get_statistics_for_service('a1b2c3d4')

    mock_get.assert_called_once_with(url=expected_url)

import uuid
from datetime import datetime

from app.notify_client.statistics_api_client import StatisticsApiClient


def test_notifications_statistics_client_calls_correct_api_endpoint(mocker, api_user_active):

    some_service_id = uuid.uuid4()
    expected_url = '/service/{}/notifications-statistics'.format(some_service_id)

    client = StatisticsApiClient()

    mock_get = mocker.patch('app.notify_client.statistics_api_client.StatisticsApiClient.get')

    client.get_statistics_for_service(some_service_id)

    mock_get.assert_called_once_with(url=expected_url, params={})


def test_notifications_statistics_client_calls_correct_api_endpoint_with_params(mocker, api_user_active):

    some_service_id = uuid.uuid4()
    expected_url = '/service/{}/notifications-statistics'.format(some_service_id)

    client = StatisticsApiClient()

    mock_get = mocker.patch('app.notify_client.statistics_api_client.StatisticsApiClient.get')

    client.get_statistics_for_service(some_service_id, limit_days=99)

    mock_get.assert_called_once_with(url=expected_url, params={'limit_days': 99})


def test_notifications_statistics_client_for_stats_by_day_calls_correct_api_endpoint(mocker, api_user_active):

    some_service_id = uuid.uuid4()
    today = datetime.today().date().strftime('%Y-%m-%d')

    expected_url = '/service/{}/notifications-statistics/day/{}'.format(some_service_id, today)

    client = StatisticsApiClient()

    mock_get = mocker.patch('app.notify_client.statistics_api_client.StatisticsApiClient.get')

    client.get_statistics_for_service_for_day(some_service_id, today)

    mock_get.assert_called_once_with(url=expected_url)

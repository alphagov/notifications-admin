from app.notify_client.performance_platform_api_client import (
    PerformancePlatformAPIClient,
)


def test_get_aggregate_platform_stats(mocker):
    client = PerformancePlatformAPIClient()
    mock = mocker.patch.object(client, 'get')
    params_dict = {'start_date': '2021-03-01', 'end_date': '2021-03-31'}

    client.get_performance_platform_stats(params_dict=params_dict)
    mock.assert_called_once_with('/performance-platform', params=params_dict)

from app.notify_client.performance_dashboard_api_client import (
    PerformanceDashboardAPIClient,
)


def test_get_aggregate_platform_stats(mocker):
    client = PerformanceDashboardAPIClient()
    mock = mocker.patch.object(client, 'get')
    params_dict = {'start_date': '2021-03-01', 'end_date': '2021-03-31'}

    client.get_performance_dashboard_stats(params_dict=params_dict)
    mock.assert_called_once_with('/performance-dashboard', params=params_dict)

from datetime import date

from app.notify_client.performance_dashboard_api_client import (
    PerformanceDashboardAPIClient,
)


def test_get_aggregate_platform_stats(mocker):
    client = PerformanceDashboardAPIClient()
    mock = mocker.patch.object(client, 'get')

    client.get_performance_dashboard_stats(
        start_date=date(2021, 3, 1),
        end_date=date(2021, 3, 31),
    )

    mock.assert_called_once_with('/performance-dashboard', params={
        'start_date': '2021-03-01',
        'end_date': '2021-03-31'
    })

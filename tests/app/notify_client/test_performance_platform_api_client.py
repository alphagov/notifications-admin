from datetime import date
from unittest.mock import call

from app.notify_client.performance_dashboard_api_client import (
    PerformanceDashboardAPIClient,
)


def test_get_aggregate_platform_stats(mocker):
    mocker.patch('app.extensions.RedisClient.get', return_value=None)
    client = PerformanceDashboardAPIClient()
    mock = mocker.patch.object(client, 'get', return_value={})

    client.get_performance_dashboard_stats(
        start_date=date(2021, 3, 1),
        end_date=date(2021, 3, 31),
    )

    mock.assert_called_once_with('/performance-dashboard', params={
        'start_date': '2021-03-01',
        'end_date': '2021-03-31'
    })


def test_sets_value_in_cache(mocker):
    client = PerformanceDashboardAPIClient()

    mock_redis_get = mocker.patch(
        'app.extensions.RedisClient.get',
        return_value=None,
    )
    mock_api_get = mocker.patch(
        'app.notify_client.NotifyAdminAPIClient.get',
        return_value={'data_from': 'api'},
    )
    mock_redis_set = mocker.patch(
        'app.extensions.RedisClient.set',
    )

    assert client.get_performance_dashboard_stats(
        start_date=date(2021, 1, 1),
        end_date=date(2022, 2, 2),
    ) == {'data_from': 'api'}

    assert mock_redis_get.call_args_list == [
        call('performance-stats-2021-01-01-to-2022-02-02'),
    ]
    assert mock_api_get.call_args_list == [
        call('/performance-dashboard', params={
            'start_date': '2021-01-01', 'end_date': '2022-02-02'
        }),
    ]
    assert mock_redis_set.call_args_list == [
        call(
            'performance-stats-2021-01-01-to-2022-02-02',
            '{"data_from": "api"}',
            ex=604800,
        ),
    ]


def test_returns_value_from_cache(mocker):
    client = PerformanceDashboardAPIClient()

    mock_redis_get = mocker.patch(
        'app.extensions.RedisClient.get',
        return_value=b'{"data_from": "cache"}',
    )
    mock_api_get = mocker.patch(
        'app.notify_client.NotifyAdminAPIClient.get',
    )
    mock_redis_set = mocker.patch(
        'app.extensions.RedisClient.set',
    )

    assert client.get_performance_dashboard_stats(
        start_date=date(2021, 1, 1),
        end_date=date(2022, 2, 2),
    ) == {'data_from': 'cache'}

    assert mock_redis_get.call_args_list == [
        call('performance-stats-2021-01-01-to-2022-02-02'),
    ]
    assert mock_api_get.called is False
    assert mock_redis_set.called is False

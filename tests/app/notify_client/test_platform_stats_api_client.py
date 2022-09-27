from app.notify_client.platform_stats_api_client import PlatformStatsAPIClient


def test_get_aggregate_platform_stats(mocker):
    client = PlatformStatsAPIClient()
    mock = mocker.patch.object(client, "get")
    params_dict = {"start_date": "2018-06-01", "end_date": "2018-06-15"}

    client.get_aggregate_platform_stats(params_dict=params_dict)
    mock.assert_called_once_with("/platform-stats", params=params_dict)

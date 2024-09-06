from app.notify_client.letter_rate_api_client import LetterRateApiClient


def test_sets_value_in_cache(mocker):
    client = LetterRateApiClient(mocker.MagicMock())

    mock_redis_get = mocker.patch("app.extensions.RedisClient.get", return_value=None)
    mock_api_get = mocker.patch(
        "app.notify_client.NotifyAdminAPIClient.get",
        return_value={"data_from": "api"},
    )
    mock_redis_set = mocker.patch(
        "app.extensions.RedisClient.set",
    )

    assert client.get_letter_rates() == {"data_from": "api"}

    mock_redis_get.assert_called_once_with("letter-rates")
    mock_api_get.assert_called_once_with(url="/letter-rates")
    mock_redis_set.assert_called_once_with("letter-rates", '{"data_from": "api"}', ex=3_600)


def test_returns_value_from_cache(mocker):
    client = LetterRateApiClient(mocker.MagicMock())

    mock_redis_get = mocker.patch(
        "app.extensions.RedisClient.get",
        return_value=b'{"data_from": "cache"}',
    )
    mock_api_get = mocker.patch(
        "app.notify_client.NotifyAdminAPIClient.get",
    )
    mock_redis_set = mocker.patch(
        "app.extensions.RedisClient.set",
    )

    assert client.get_letter_rates() == {"data_from": "cache"}

    mock_redis_get.assert_called_once_with("letter-rates")

    assert mock_api_get.called is False
    assert mock_redis_set.called is False

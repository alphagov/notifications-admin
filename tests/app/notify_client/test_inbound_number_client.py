import pytest

from app.notify_client.inbound_number_client import inbound_number_client


@pytest.mark.parametrize(
    "inbound_number_id, data",
    [
        (None, {}),
        ("1234", {"inbound_number_id": "1234"}),
    ],
)
def test_add_inbound_number_to_service(mocker, inbound_number_id, data):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete")
    mock_redis_delete_by_pattern = mocker.patch("app.extensions.RedisClient.delete_by_pattern")
    mock_post = mocker.patch("app.notify_client.inbound_number_client.InboundNumberClient.post")

    inbound_number_client.add_inbound_number_to_service("abcd", inbound_number_id=inbound_number_id)

    mock_post.assert_called_once_with("inbound-number/service/abcd", data=data)

    assert mock_redis_delete.call_args_list == [mocker.call("service-abcd")]
    assert mock_redis_delete_by_pattern.call_args_list == [mocker.call("service-abcd-template-*")]

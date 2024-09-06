from app.notify_client.letter_branding_client import LetterBrandingClient
from tests.utils import RedisClientMock


def test_get_letter_branding(mocker, fake_uuid):
    mock_get = mocker.patch(
        "app.notify_client.letter_branding_client.LetterBrandingClient.get", return_value={"foo": "bar"}
    )
    mock_redis_get = mocker.patch("app.extensions.RedisClient.get", return_value=None)
    mock_redis_set = mocker.patch("app.extensions.RedisClient.set")

    LetterBrandingClient(mocker.MagicMock()).get_letter_branding(fake_uuid)

    mock_get.assert_called_once_with(url=f"/letter-branding/{fake_uuid}")
    mock_redis_get.assert_called_once_with(f"letter_branding-{fake_uuid}")
    mock_redis_set.assert_called_once_with(
        f"letter_branding-{fake_uuid}",
        '{"foo": "bar"}',
        ex=2_419_200,
    )


def test_get_all_letter_branding(mocker):
    mock_get = mocker.patch("app.notify_client.letter_branding_client.LetterBrandingClient.get", return_value=[1, 2, 3])
    mock_redis_get = mocker.patch("app.extensions.RedisClient.get", return_value=None)
    mock_redis_set = mocker.patch("app.extensions.RedisClient.set")

    LetterBrandingClient(mocker.MagicMock()).get_all_letter_branding()

    mock_get.assert_called_once_with(url="/letter-branding")
    mock_redis_get.assert_called_once_with("letter_branding")
    mock_redis_set.assert_called_once_with(
        "letter_branding",
        "[1, 2, 3]",
        ex=2_419_200,
    )


def test_get_unique_name_for_letter_branding(mocker):
    mock_post = mocker.patch(
        "app.notify_client.letter_branding_client.LetterBrandingClient.post", return_value={"name": "some unique name"}
    )

    ret = LetterBrandingClient(mocker.MagicMock()).get_unique_name_for_letter_branding("some name")

    mock_post.assert_called_once_with(url="/letter-branding/get-unique-name", data={"name": "some name"})
    assert ret == "some unique name"


def test_create_letter_branding(mocker):
    new_branding = {"filename": "uuid-test", "name": "my letters", "created_by_id": "1234"}

    mock_post = mocker.patch("app.notify_client.letter_branding_client.LetterBrandingClient.post")
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete", new_callable=RedisClientMock)

    LetterBrandingClient(mocker.MagicMock()).create_letter_branding(
        filename=new_branding["filename"],
        name=new_branding["name"],
        created_by_id=new_branding["created_by_id"],
    )
    mock_post.assert_called_once_with(url="/letter-branding", data=new_branding)

    mock_redis_delete.assert_called_with_args("letter_branding")


def test_update_letter_branding(mocker, fake_uuid):
    branding = {"filename": "uuid-test", "name": "my letters", "updated_by_id": "1234"}

    mock_post = mocker.patch("app.notify_client.letter_branding_client.LetterBrandingClient.post")
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete", new_callable=RedisClientMock)
    mock_redis_delete_by_pattern = mocker.patch(
        "app.extensions.RedisClient.delete_by_pattern", new_callable=RedisClientMock
    )
    LetterBrandingClient(mocker.MagicMock()).update_letter_branding(
        branding_id=fake_uuid,
        filename=branding["filename"],
        name=branding["name"],
        updated_by_id=branding["updated_by_id"],
    )

    mock_post.assert_called_once_with(url=f"/letter-branding/{fake_uuid}", data=branding)
    mock_redis_delete.assert_called_with_args(
        f"letter_branding-{fake_uuid}",
        "letter_branding",
    )
    mock_redis_delete_by_pattern.assert_called_with_args("organisation-*-letter-branding-pool")

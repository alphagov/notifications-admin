from app import letter_jobs_client
from tests.utils import RedisClientMock


def test_submit_returned_letters(mocker):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete_by_pattern", new_callable=RedisClientMock)
    mock_post = mocker.patch("app.notify_client.letter_jobs_client.LetterJobsClient.post")

    letter_jobs_client.submit_returned_letters(["reference1", "reference2"])

    mock_post.assert_called_with(url="/letters/returned", data={"references": ["reference1", "reference2"]})

    mock_redis_delete.assert_called_with_args(
        "service-????????-????-????-????-????????????-returned-letters-statistics",
        "service-????????-????-????-????-????????????-returned-letters-summary",
    )

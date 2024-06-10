from app import letter_jobs_client
from tests.utils import assert_mock_has_any_call_with_first_n_args


def test_submit_returned_letters(mocker, fake_uuid):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete_by_pattern")
    mock_post = mocker.patch("app.notify_client.letter_jobs_client.LetterJobsClient.post")

    letter_jobs_client.submit_returned_letters(["reference1", "reference2"])

    mock_post.assert_called_with(url="/letters/returned", data={"references": ["reference1", "reference2"]})

    assert_mock_has_any_call_with_first_n_args(
        mock_redis_delete, "service-????????-????-????-????-????????????-returned-letters-statistics"
    )
    assert_mock_has_any_call_with_first_n_args(
        mock_redis_delete, "service-????????-????-????-????-????????????-returned-letters-summary"
    )

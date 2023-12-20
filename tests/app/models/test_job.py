import pytest

from app.models.job import Job
from tests import job_json, user_json
from tests.conftest import SERVICE_ONE_ID


@pytest.mark.parametrize(
    "job_status, num_notifications_created, expected_still_processing",
    [
        ("scheduled", 0, True),
        ("cancelled", 10, True),
        ("finished", 5, True),
        ("finished", 10, False),
    ],
)
def test_still_processing(notify_admin, job_status, num_notifications_created, expected_still_processing):
    json = job_json(
        service_id=SERVICE_ONE_ID,
        created_by=user_json(),
        notification_count=10,
        notifications_requested=num_notifications_created,
        job_status=job_status,
    )
    job = Job(json)
    assert job.still_processing == expected_still_processing


@pytest.mark.parametrize(
    "failed, delivered, expected_failure_rate", [(0, 0, 0), (0, 1, 0), (1, 1, 50), (1, 0, 100), (1, 4, 20)]
)
def test_add_rate_to_job_calculates_rate(failed, delivered, expected_failure_rate):
    resp = Job(
        {
            "statistics": [
                {"status": "failed", "count": failed},
                {"status": "delivered", "count": delivered},
            ],
            "id": "foo",
        }
    )

    assert resp.failure_rate == expected_failure_rate


def test_add_rate_to_job_preserves_initial_fields():
    resp = Job(
        {
            "statistics": [
                {"status": "failed", "count": 0},
                {"status": "delivered", "count": 0},
            ],
            "id": "foo",
        }
    )

    assert resp.notifications_failed == resp.notifications_delivered == resp.failure_rate == 0
    assert resp.id == "foo"

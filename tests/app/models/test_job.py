import pytest

from app.models.job import Job
from tests import job_json, user_json
from tests.conftest import SERVICE_ONE_ID


@pytest.mark.parametrize(
    'job_status, num_notifications_created, expected_still_processing',
    [
        ('scheduled', 0, True),
        ('cancelled', 10, True),
        ('finished', 5, True),
        ('finished', 10, False),
    ]
)
def test_still_processing(
    notify_admin,
    job_status,
    num_notifications_created,
    expected_still_processing
):
    json = job_json(
        service_id=SERVICE_ONE_ID,
        created_by=user_json(),
        notification_count=10,
        notifications_requested=num_notifications_created,
        job_status=job_status
    )
    job = Job(json)
    assert job.still_processing == expected_still_processing

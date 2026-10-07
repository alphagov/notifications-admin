from uuid import UUID
from app.models.contact_list import ContactList
from app.models.job import PaginatedJobs


def test_get_jobs(mock_get_jobs):
    contact_list = ContactList({"id": str(UUID(version=4, int=1)), "service_id": str(UUID(version=4, int=2))})
    assert isinstance(contact_list.get_jobs(page=123), PaginatedJobs)
    # mock_get_jobs mocks the underlying API client method, not
    # contact_list.get_jobs
    mock_get_jobs.assert_called_once_with(
        str(UUID(version=4, int=2)),
        contact_list_id=str(UUID(version=4, int=1)),
        statuses={
            "finished all notifications created",
            "finished",
            "sending limits exceeded",
            "ready to send",
            "scheduled",
            "sent to dvla",
            "pending",
            "in progress",
        },
        page=123,
        limit_days=None,
    )

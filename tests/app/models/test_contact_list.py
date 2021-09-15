from app.models.contact_list import ContactList
from app.models.job import PaginatedJobs


def test_get_jobs(mock_get_jobs):
    contact_list = ContactList({'id': 'a', 'service_id': 'b'})
    assert isinstance(contact_list.get_jobs(page=123), PaginatedJobs)
    # mock_get_jobs mocks the underlying API client method, not
    # contact_list.get_jobs
    mock_get_jobs.assert_called_once_with(
        'b',
        contact_list_id='a',
        statuses={
            'finished',
            'sending limits exceeded',
            'ready to send',
            'scheduled',
            'sent to dvla',
            'pending',
            'in progress',
        },
        page=123,
        limit_days=None,
    )

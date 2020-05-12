from datetime import datetime

from app.models.contact_list import ContactList
from app.models.job import PaginatedJobs


def test_created_at():
    created_at = ContactList({'created_at': '2016-05-06T07:08:09.061258'}).created_at
    assert isinstance(created_at, datetime)
    assert created_at.isoformat() == '2016-05-06T08:08:09.061258+01:00'


def test_get_jobs(mock_get_jobs):
    contact_list = ContactList({'id': 'a', 'service_id': 'b'})
    assert isinstance(contact_list.get_jobs(page=123), PaginatedJobs)
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
    )

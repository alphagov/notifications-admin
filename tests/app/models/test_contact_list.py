from datetime import datetime

from app.models.contact_list import ContactList


def test_created_at():
    created_at = ContactList({'created_at': '2016-05-06T07:08:09.061258'}).created_at
    assert isinstance(created_at, datetime)
    assert created_at.isoformat() == '2016-05-06T08:08:09.061258+01:00'

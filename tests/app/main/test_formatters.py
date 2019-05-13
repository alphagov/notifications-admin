from functools import partial

import pytest
from flask import url_for

from app import format_notification_status_as_url


@pytest.mark.parametrize('status, notification_type, expected', (
    # Successful statuses aren’t linked
    ('created', 'email', lambda: None),
    ('sending', 'email', lambda: None),
    ('delivered', 'email', lambda: None),
    # Failures are linked to the channel-specific page
    ('temporary-failure', 'email', partial(url_for, 'main.message_status', _anchor='email-statuses')),
    ('permanent-failure', 'email', partial(url_for, 'main.message_status', _anchor='email-statuses')),
    ('technical-failure', 'email', partial(url_for, 'main.message_status', _anchor='email-statuses')),
    ('temporary-failure', 'sms', partial(url_for, 'main.message_status', _anchor='sms-statuses')),
    ('permanent-failure', 'sms', partial(url_for, 'main.message_status', _anchor='sms-statuses')),
    ('technical-failure', 'sms', partial(url_for, 'main.message_status', _anchor='sms-statuses')),
    # Letter statuses are never linked
    ('technical-failure', 'letter', lambda: None),
    ('cancelled', 'letter', lambda: None),
    ('accepted', 'letter', lambda: None),
    ('received', 'letter', lambda: None),
))
def test_format_notification_status_as_url(
    client,
    status,
    notification_type,
    expected,
):
    assert format_notification_status_as_url(
        status, notification_type
    ) == expected()

from functools import partial

import pytest
from flask import url_for

from app import (
    format_notification_status_as_url,
    format_number_in_pounds_as_currency,
)


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


@pytest.mark.parametrize('input_number, formatted_number', [
    (0, '0p'),
    (0.01, '1p'),
    (0.5, '50p'),
    (1, '£1.00'),
    (1.01, '£1.01'),
    (1.006, '£1.01'),
    (5.25, '£5.25'),
    (5.7, '£5.70'),
    (381, '£381.00'),
    (144820, '£144,820.00'),
])
def test_format_number_in_pounds_as_currency(input_number, formatted_number):
    assert format_number_in_pounds_as_currency(input_number) == formatted_number

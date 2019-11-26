from collections import namedtuple

import pytest

from app.utils import get_errors_for_csv

MockRecipients = namedtuple(
    'RecipientCSV',
    [
        'rows_with_bad_recipients',
        'rows_with_missing_data',
        'rows_with_message_too_long',
        'rows_with_empty_message'
    ]
)


@pytest.mark.parametrize(
    "rows_with_bad_recipients, rows_with_missing_data, "
    "rows_with_message_too_long, rows_with_empty_message, template_type, expected_errors",
    [
        (
            [], [], [], [],
            'sms',
            []
        ),
        (
            {2}, [], [], [],
            'sms',
            ['fix 1 phone number']
        ),
        (
            {2, 4, 6}, [], [], [],
            'sms',
            ['fix 3 phone numbers']
        ),
        (
            {1}, [], [], [],
            'email',
            ['fix 1 email address']
        ),
        (
            {2, 4, 6}, [], [], [],
            'email',
            ['fix 3 email addresses']
        ),
        (
            {2}, {3}, [], [],
            'sms',
            [
                'fix 1 phone number',
                'enter missing data in 1 row'
            ]
        ),
        (
            {2, 4, 6, 8}, {3, 6, 9, 12}, [], [],
            'sms',
            [
                'fix 4 phone numbers',
                'enter missing data in 4 rows'
            ]
        ),
        (
            {}, {}, {3}, [],
            'sms',
            [
                'shorten your message in 1 row'
            ]
        ),
        (
            {}, {}, {3, 12}, [],
            'sms',
            [
                'shorten your messages in 2 rows'
            ]
        ),
        (
            {}, {}, {}, {2},
            'sms',
            [
                'add content to empty message in 1 row'
            ]
        ),
        (
            {}, {}, {}, {2, 4, 8},
            'sms',
            [
                'add content to empty messages in 3 rows'
            ]
        ),
    ]
)
def test_get_errors_for_csv(
    rows_with_bad_recipients, rows_with_missing_data, rows_with_message_too_long, rows_with_empty_message,
    template_type,
    expected_errors
):
    assert get_errors_for_csv(
        MockRecipients(
            rows_with_bad_recipients, rows_with_missing_data, rows_with_message_too_long, rows_with_empty_message
        ),
        template_type
    ) == expected_errors

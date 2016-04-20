from collections import namedtuple

import pytest

from app.utils import get_errors_for_csv


MockRecipients = namedtuple(
    'RecipientCSV',
    [
        'missing_column_headers',
        'rows_with_bad_recipients',
        'rows_with_missing_data'
    ]
)


@pytest.mark.parametrize(
    "missing_column_headers,rows_with_bad_recipients,rows_with_missing_data,template_type,expected_errors",
    [
        (
            [], [], [],
            'sms',
            []
        ),
        (
            [], {2}, [],
            'sms',
            ['fix 1 phone number']
        ),
        (
            [], {2, 4, 6}, [],
            'sms',
            ['fix 3 phone numbers']
        ),
        (
            [], {1}, [],
            'email',
            ['fix 1 email address']
        ),
        (
            [], {2, 4, 6}, [],
            'email',
            ['fix 3 email addresses']
        ),
        (
            ['name'], {2}, {3},
            'sms',
            [
                'add a column called ‘name’',
                'fix 1 phone number',
                'enter missing data in 1 row'
            ]
        ),
        (
            ['name', 'date'], [], [],
            'sms',
            ['add 2 columns, ‘name’ and ‘date’']
        ),
        (
            ['name', 'date', 'time'], {2, 4, 6, 8}, {3, 6, 9, 12},
            'sms',
            [
                'add columns called ‘name’, ‘date’, and ‘time’',
                'fix 4 phone numbers',
                'enter missing data in 4 rows'
            ]
        )
    ]
)
def test_get_errors_for_csv(
    missing_column_headers, rows_with_bad_recipients, rows_with_missing_data,
    template_type,
    expected_errors
):
    assert get_errors_for_csv(
        MockRecipients(missing_column_headers, rows_with_bad_recipients, rows_with_missing_data),
        template_type
    ) == expected_errors

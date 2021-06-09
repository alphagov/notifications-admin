from collections import OrderedDict, namedtuple
from csv import DictReader
from io import StringIO
from pathlib import Path

import pytest

from app.utils.csv import (
    Spreadsheet,
    generate_notifications_csv,
    get_errors_for_csv,
)
from tests.conftest import fake_uuid


def _get_notifications_csv(
    row_number=1,
    recipient='foo@bar.com',
    template_name='foo',
    template_type='sms',
    job_name='bar.csv',
    status='Delivered',
    created_at='1943-04-19 12:00:00',
    rows=1,
    with_links=False,
    job_id=fake_uuid,
    created_by_name=None,
    created_by_email_address=None,
):

    def _get(
        service_id,
        page=1,
        job_id=None,
        template_type=template_type,
    ):
        links = {}
        if with_links:
            links = {
                'prev': '/service/{}/notifications?page=0'.format(service_id),
                'next': '/service/{}/notifications?page=1'.format(service_id),
                'last': '/service/{}/notifications?page=2'.format(service_id)
            }

        data = {
            'notifications': [{
                "row_number": row_number + i,
                "to": recipient,
                "recipient": recipient,
                "client_reference": 'ref 1234',
                "template_name": template_name,
                "template_type": template_type,
                "template": {"name": template_name, "template_type": template_type},
                "job_name": job_name,
                "status": status,
                "created_at": created_at,
                "updated_at": None,
                "created_by_name": created_by_name,
                "created_by_email_address": created_by_email_address,
            } for i in range(rows)],
            'total': rows,
            'page_size': 50,
            'links': links
        }

        return data

    return _get


@pytest.fixture(scope='function')
def _get_notifications_csv_mock(
    mocker,
    api_user_active,
):
    return mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=_get_notifications_csv()
    )


def test_can_create_spreadsheet_from_large_excel_file():
    with open(str(Path.cwd() / 'tests' / 'spreadsheet_files' / 'excel 2007.xlsx'), 'rb') as xl:
        ret = Spreadsheet.from_file(xl, filename='xl.xlsx')
    assert ret.as_csv_data


def test_can_create_spreadsheet_from_dict():
    assert Spreadsheet.from_dict(OrderedDict(
        foo='bar',
        name='Jane',
    )).as_csv_data == (
        "foo,name\r\n"
        "bar,Jane\r\n"
    )


def test_can_create_spreadsheet_from_dict_with_filename():
    assert Spreadsheet.from_dict({}, filename='empty.csv').as_dict['file_name'] == "empty.csv"


@pytest.mark.parametrize('args, kwargs', (
    (
        ('hello', ['hello']),
        {},
    ),
    (
        (),
        {'csv_data': 'hello', 'rows': ['hello']}
    ),
))
def test_spreadsheet_checks_for_bad_arguments(args, kwargs):
    with pytest.raises(TypeError) as exception:
        Spreadsheet(*args, **kwargs)
    assert str(exception.value) == 'Spreadsheet must be created from either rows or CSV data'


@pytest.mark.parametrize('created_by_name, expected_content', [
    (
        None, [
            'Recipient,Reference,Template,Type,Sent by,Sent by email,Job,Status,Time\n',
            'foo@bar.com,ref 1234,foo,sms,,sender@email.gov.uk,,Delivered,1943-04-19 12:00:00\r\n',
        ]
    ),
    (
        'Anne Example', [
            'Recipient,Reference,Template,Type,Sent by,Sent by email,Job,Status,Time\n',
            'foo@bar.com,ref 1234,foo,sms,Anne Example,sender@email.gov.uk,,Delivered,1943-04-19 12:00:00\r\n',
        ]
    ),
])
def test_generate_notifications_csv_without_job(
    notify_admin,
    mocker,
    created_by_name,
    expected_content,
):
    mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=_get_notifications_csv(
            created_by_name=created_by_name,
            created_by_email_address="sender@email.gov.uk",
            job_id=None,
            job_name=None
        )
    )
    assert list(generate_notifications_csv(service_id=fake_uuid)) == expected_content


@pytest.mark.parametrize('original_file_contents, expected_column_headers, expected_1st_row', [
    (
        """
            phone_number
            07700900123
        """,
        ['Row number', 'phone_number', 'Template', 'Type', 'Job', 'Status', 'Time'],
        ['1', '07700900123', 'foo', 'sms', 'bar.csv', 'Delivered', '1943-04-19 12:00:00'],
    ),
    (
        """
            phone_number, a, b, c
            07700900123,  🐜,🐝,🦀
        """,
        ['Row number', 'phone_number', 'a', 'b', 'c', 'Template', 'Type', 'Job', 'Status', 'Time'],
        ['1', '07700900123', '🐜', '🐝', '🦀', 'foo', 'sms', 'bar.csv', 'Delivered', '1943-04-19 12:00:00'],
    ),
    (
        """
            "phone_number", "a", "b", "c"
            "07700900123","🐜,🐜","🐝,🐝","🦀"
        """,
        ['Row number', 'phone_number', 'a', 'b', 'c', 'Template', 'Type', 'Job', 'Status', 'Time'],
        ['1', '07700900123', '🐜,🐜', '🐝,🐝', '🦀', 'foo', 'sms', 'bar.csv', 'Delivered', '1943-04-19 12:00:00'],
    ),
])
def test_generate_notifications_csv_returns_correct_csv_file(
    notify_admin,
    mocker,
    _get_notifications_csv_mock,
    original_file_contents,
    expected_column_headers,
    expected_1st_row,
):
    mocker.patch(
        'app.s3_client.s3_csv_client.s3download',
        return_value=original_file_contents,
    )
    csv_content = generate_notifications_csv(service_id='1234', job_id=fake_uuid, template_type='sms')
    csv_file = DictReader(StringIO('\n'.join(csv_content)))
    assert csv_file.fieldnames == expected_column_headers
    assert next(csv_file) == dict(zip(expected_column_headers, expected_1st_row))


def test_generate_notifications_csv_only_calls_once_if_no_next_link(
    notify_admin,
    _get_notifications_csv_mock,
):
    list(generate_notifications_csv(service_id='1234'))

    assert _get_notifications_csv_mock.call_count == 1


@pytest.mark.parametrize("job_id", ["some", None])
def test_generate_notifications_csv_calls_twice_if_next_link(
    notify_admin,
    mocker,
    job_id,
):

    mocker.patch(
        'app.s3_client.s3_csv_client.s3download',
        return_value="""
            phone_number
            07700900000
            07700900001
            07700900002
            07700900003
            07700900004
            07700900005
            07700900006
            07700900007
            07700900008
            07700900009
        """
    )

    service_id = '1234'
    response_with_links = _get_notifications_csv(rows=7, with_links=True)
    response_with_no_links = _get_notifications_csv(rows=3, row_number=8, with_links=False)

    mock_get_notifications = mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=[
            response_with_links(service_id),
            response_with_no_links(service_id),
        ]
    )

    csv_content = generate_notifications_csv(
        service_id=service_id,
        job_id=job_id or fake_uuid,
        template_type='sms',
    )
    csv = list(DictReader(StringIO('\n'.join(csv_content))))

    assert len(csv) == 10
    assert csv[0]['phone_number'] == '07700900000'
    assert csv[9]['phone_number'] == '07700900009'
    assert mock_get_notifications.call_count == 2
    # mock_calls[0][2] is the kwargs from first call
    assert mock_get_notifications.mock_calls[0][2]['page'] == 1
    assert mock_get_notifications.mock_calls[1][2]['page'] == 2


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
            {2}, [], [], [],
            'letter',
            ['fix 1 address']
        ),
        (
            {2, 4}, [], [], [],
            'letter',
            ['fix 2 addresses']
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
                'shorten the message in 1 row'
            ]
        ),
        (
            {}, {}, {3, 12}, [],
            'sms',
            [
                'shorten the messages in 2 rows'
            ]
        ),
        (
            {}, {}, {}, {2},
            'sms',
            [
                'check you have content for the empty message in 1 row'
            ]
        ),
        (
            {}, {}, {}, {2, 4, 8},
            'sms',
            [
                'check you have content for the empty messages in 3 rows'
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

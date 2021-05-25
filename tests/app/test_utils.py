from collections import OrderedDict
from csv import DictReader
from io import StringIO
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from freezegun import freeze_time
from notifications_utils.template import Template

from app import format_datetime_relative
from app.formatters import email_safe, round_to_significant_figures
from app.utils import (
    Spreadsheet,
    generate_next_dict,
    generate_notifications_csv,
    generate_previous_dict,
    get_current_financial_year,
    get_letter_printing_statement,
    get_letter_validation_error,
    get_logo_cdn_domain,
    get_sample_template,
    is_less_than_days_ago,
    merge_jsonlike,
    printing_today_or_tomorrow,
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


@pytest.mark.parametrize('service_name, safe_email', [
    ('name with spaces', 'name.with.spaces'),
    ('singleword', 'singleword'),
    ('UPPER CASE', 'upper.case'),
    ('Service - with dash', 'service.with.dash'),
    ('lots      of spaces', 'lots.of.spaces'),
    ('name.with.dots', 'name.with.dots'),
    ('name-with-other-delimiters', 'namewithotherdelimiters'),
    ('.leading', 'leading'),
    ('trailing.', 'trailing'),
    ('üńïçödë wördś', 'unicode.words'),
])
def test_email_safe_return_dot_separated_email_domain(service_name, safe_email):
    assert email_safe(service_name) == safe_email


def test_generate_previous_dict(client):
    ret = generate_previous_dict('main.view_jobs', 'foo', 2, {})
    assert 'page=1' in ret['url']
    assert ret['title'] == 'Previous page'
    assert ret['label'] == 'page 1'


def test_generate_next_dict(client):
    ret = generate_next_dict('main.view_jobs', 'foo', 2, {})
    assert 'page=3' in ret['url']
    assert ret['title'] == 'Next page'
    assert ret['label'] == 'page 3'


def test_generate_previous_next_dict_adds_other_url_args(client):
    ret = generate_next_dict('main.view_notifications', 'foo', 2, {'message_type': 'blah'})
    assert 'notifications/blah' in ret['url']


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


def test_get_cdn_domain_on_localhost(client, mocker):
    mocker.patch.dict('app.current_app.config', values={'ADMIN_BASE_URL': 'http://localhost:6012'})
    domain = get_logo_cdn_domain()
    assert domain == 'static-logos.notify.tools'


def test_get_cdn_domain_on_non_localhost(client, mocker):
    mocker.patch.dict('app.current_app.config', values={'ADMIN_BASE_URL': 'https://some.admintest.com'})
    domain = get_logo_cdn_domain()
    assert domain == 'static-logos.admintest.com'


@pytest.mark.parametrize('time, human_readable_datetime', [
    ('2018-03-14 09:00', '14 March at 9:00am'),
    ('2018-03-14 15:00', '14 March at 3:00pm'),

    ('2018-03-15 09:00', '15 March at 9:00am'),
    ('2018-03-15 15:00', '15 March at 3:00pm'),

    ('2018-03-19 09:00', '19 March at 9:00am'),
    ('2018-03-19 15:00', '19 March at 3:00pm'),
    ('2018-03-19 23:59', '19 March at 11:59pm'),

    ('2018-03-20 00:00', '19 March at midnight'),  # we specifically refer to 00:00 as belonging to the day before.
    ('2018-03-20 00:01', 'yesterday at 12:01am'),
    ('2018-03-20 09:00', 'yesterday at 9:00am'),
    ('2018-03-20 15:00', 'yesterday at 3:00pm'),
    ('2018-03-20 23:59', 'yesterday at 11:59pm'),

    ('2018-03-21 00:00', 'yesterday at midnight'),  # we specifically refer to 00:00 as belonging to the day before.
    ('2018-03-21 00:01', 'today at 12:01am'),
    ('2018-03-21 09:00', 'today at 9:00am'),
    ('2018-03-21 12:00', 'today at midday'),
    ('2018-03-21 15:00', 'today at 3:00pm'),
    ('2018-03-21 23:59', 'today at 11:59pm'),

    ('2018-03-22 00:00', 'today at midnight'),  # we specifically refer to 00:00 as belonging to the day before.
    ('2018-03-22 00:01', 'tomorrow at 12:01am'),
    ('2018-03-22 09:00', 'tomorrow at 9:00am'),
    ('2018-03-22 15:00', 'tomorrow at 3:00pm'),
    ('2018-03-22 23:59', 'tomorrow at 11:59pm'),

    ('2018-03-23 00:01', '23 March at 12:01am'),
    ('2018-03-23 09:00', '23 March at 9:00am'),
    ('2018-03-23 15:00', '23 March at 3:00pm'),

])
def test_format_datetime_relative(time, human_readable_datetime):
    with freeze_time('2018-03-21 12:00'):
        assert format_datetime_relative(time) == human_readable_datetime


@pytest.mark.parametrize('utc_datetime', [
    '2018-08-01T23:00:00+00:00',
    '2018-08-01T16:29:00+00:00',
    '2018-11-01T00:00:00+00:00',
    '2018-11-01T10:00:00+00:00',
    '2018-11-01T17:29:00+00:00',
])
def test_printing_today_or_tomorrow_returns_today(utc_datetime):
    with freeze_time(utc_datetime):
        assert printing_today_or_tomorrow(utc_datetime) == 'today'


@pytest.mark.parametrize('utc_datetime', [
    '2018-08-01T22:59:00+00:00',
    '2018-08-01T16:30:00+00:00',
    '2018-11-01T17:30:00+00:00',
    '2018-11-01T21:00:00+00:00',
    '2018-11-01T23:59:00+00:00',
])
def test_printing_today_or_tomorrow_returns_tomorrow(utc_datetime):
    with freeze_time(utc_datetime):
        assert printing_today_or_tomorrow(utc_datetime) == 'tomorrow'


@pytest.mark.parametrize('created_at, current_datetime', [
    ('2017-07-07T12:00:00+00:00', '2017-07-07 16:29:00'),  # created today, summer
    ('2017-07-06T23:30:00+00:00', '2017-07-07 16:29:00'),  # created just after midnight, summer
    ('2017-12-12T12:00:00+00:00', '2017-12-12 17:29:00'),  # created today, winter
    ('2017-12-12T21:30:00+00:00', '2017-12-13 17:29:00'),  # created after 5:30 yesterday
    ('2017-03-25T17:31:00+00:00', '2017-03-26 16:29:00'),  # over clock change period on 2017-03-26
])
def test_get_letter_printing_statement_when_letter_prints_today(created_at, current_datetime):
    with freeze_time(current_datetime):
        statement = get_letter_printing_statement('created', created_at)

    assert statement == 'Printing starts today at 5:30pm'


@pytest.mark.parametrize('created_at, current_datetime', [
    ('2017-07-07T16:31:00+00:00', '2017-07-07 22:59:00'),  # created today, summer
    ('2017-12-12T17:31:00+00:00', '2017-12-12 23:59:00'),  # created today, winter
])
def test_get_letter_printing_statement_when_letter_prints_tomorrow(created_at, current_datetime):
    with freeze_time(current_datetime):
        statement = get_letter_printing_statement('created', created_at)

    assert statement == 'Printing starts tomorrow at 5:30pm'


@pytest.mark.parametrize('created_at, print_day', [
    ('2017-07-06T16:29:00+00:00', 'yesterday'),
    ('2017-12-01T00:00:00+00:00', 'on 1 December'),
    ('2017-03-26T12:00:00+00:00', 'on 26 March'),
])
@freeze_time('2017-07-07 12:00:00')
def test_get_letter_printing_statement_for_letter_that_has_been_sent(created_at, print_day):
    statement = get_letter_printing_statement('delivered', created_at)

    assert statement == 'Printed {} at 5:30pm'.format(print_day)


def test_get_letter_validation_error_for_unknown_error():
    assert get_letter_validation_error('Unknown error') == {
        'title': 'Validation failed'
    }


@pytest.mark.parametrize('error_message, invalid_pages, expected_title, expected_content, expected_summary', [
    (
        'letter-not-a4-portrait-oriented',
        [2],
        'Your letter is not A4 portrait size',
        (
            'You need to change the size or orientation of page 2. '
            'Files must meet our letter specification.'
        ),
        (
            'Validation failed because page 2 is not A4 portrait size.'
            'Files must meet our letter specification.'
        ),
    ),
    (
        'letter-not-a4-portrait-oriented',
        [2, 3, 4],
        'Your letter is not A4 portrait size',
        (
            'You need to change the size or orientation of pages 2, 3 and 4. '
            'Files must meet our letter specification.'
        ),
        (
            'Validation failed because pages 2, 3 and 4 are not A4 portrait size.'
            'Files must meet our letter specification.'
        ),
    ),
    (
        'content-outside-printable-area',
        [2],
        'Your content is outside the printable area',
        (
            'You need to edit page 2.'
            'Files must meet our letter specification.'
        ),
        (
            'Validation failed because content is outside the printable area '
            'on page 2.'
            'Files must meet our letter specification.'
        ),
    ),
    (
        'letter-too-long',
        None,
        'Your letter is too long',
        (
            'Letters must be 10 pages or less (5 double-sided sheets of paper). '
            'Your letter is 13 pages long.'
        ),
        (
            'Validation failed because this letter is 13 pages long.'
            'Letters must be 10 pages or less (5 double-sided sheets of paper).'
        ),
    ),
    (
        'unable-to-read-the-file',
        None,
        'There’s a problem with your file',
        (
            'Notify cannot read this PDF.'
            'Save a new copy of your file and try again.'
        ),
        (
            'Validation failed because Notify cannot read this PDF.'
            'Save a new copy of your file and try again.'
        ),
    ),
    (
        'address-is-empty',
        None,
        'The address block is empty',
        (
            'You need to add a recipient address.'
            'Files must meet our letter specification.'
        ),
        (
            'Validation failed because the address block is empty.'
            'Files must meet our letter specification.'
        ),
    ),
    (
        'not-a-real-uk-postcode',
        None,
        'There’s a problem with the address for this letter',
        (
            'The last line of the address must be a real UK postcode.'
        ),
        (
            'Validation failed because the last line of the address is not a real UK postcode.'
        ),
    ),
    (
        'cant-send-international-letters',
        None,
        'There’s a problem with the address for this letter',
        (
            'You do not have permission to send letters to other countries.'
        ),
        (
            'Validation failed because your service cannot send letters to other countries.'
        ),
    ),
    (
        'not-a-real-uk-postcode-or-country',
        None,
        'There’s a problem with the address for this letter',
        (
            'The last line of the address must be a UK postcode or '
            'another country.'
        ),
        (
            'Validation failed because the last line of the address is '
            'not a UK postcode or another country.'
        ),
    ),
    (
        'not-enough-address-lines',
        None,
        'There’s a problem with the address for this letter',
        (
            'The address must be at least 3 lines long.'
        ),
        (
            'Validation failed because the address must be at least 3 lines long.'
        ),
    ),
    (
        'too-many-address-lines',
        None,
        'There’s a problem with the address for this letter',
        (
            'The address must be no more than 7 lines long.'
        ),
        (
            'Validation failed because the address must be no more than 7 lines long.'
        ),
    ),
    (
        'invalid-char-in-address',
        None,
        'There’s a problem with the address for this letter',
        (
            'Address lines must not start with any of the following characters: @ ( ) = [ ] ” \\ / , < > ~'
        ),
        (
            'Validation failed because address lines must not start with any of the following '
            'characters: @ ( ) = [ ] ” \\ / , < > ~'
        ),
    ),
])
def test_get_letter_validation_error_for_known_errors(
    client_request,
    error_message,
    invalid_pages,
    expected_title,
    expected_content,
    expected_summary,
):
    error = get_letter_validation_error(error_message, invalid_pages=invalid_pages, page_count=13)
    detail = BeautifulSoup(error['detail'], 'html.parser')
    summary = BeautifulSoup(error['summary'], 'html.parser')

    assert error['title'] == expected_title

    assert detail.text == expected_content
    if detail.select_one('a'):
        assert detail.select_one('a')['href'] == url_for('.letter_specification')

    assert summary.text == expected_summary
    if summary.select_one('a'):
        assert summary.select_one('a')['href'] == url_for('.letter_specification')


@pytest.mark.parametrize("date_from_db, expected_result", [
    ('2019-11-17T11:35:21.726132Z', True),
    ('2019-11-16T11:35:21.726132Z', False),
    ('2019-11-16T11:35:21+0000', False),
])
@freeze_time('2020-02-14T12:00:00')
def test_is_less_than_days_ago(date_from_db, expected_result):
    assert is_less_than_days_ago(date_from_db, 90) == expected_result


@pytest.mark.parametrize("template_type", ["sms", "letter", "email"])
def test_get_sample_template_returns_template(template_type):
    template = get_sample_template(template_type)
    assert isinstance(template, Template)


@pytest.mark.parametrize("source_object, destination_object, expected_result", [
    # simple dicts:
    ({"a": "b"}, {"c": "d"}, {"a": "b", "c": "d"}),
    # dicts with nested dict, both under same key, additive behaviour:
    ({"a": {"b": "c"}}, {"a": {"e": "f"}}, {"a": {"b": "c", "e": "f"}}),
    # same key in both dicts, value is a string, destination supercedes source:
    ({"a": "b"}, {"a": "c"}, {"a": "c"}),
    # nested dict added to new key of dict, additive behaviour:
    ({"a": "b"}, {"c": {"d": "e"}}, {"a": "b", "c": {"d": "e"}}),
    # lists with same length but different items, destination supercedes source:
    (["b", "c", "d"], ["b", "e", "f"], ["b", "e", "f"]),
    # lists in dicts behave as top level lists
    ({"a": ["b", "c", "d"]}, {"a": ["b", "e", "f"]}, {"a": ["b", "e", "f"]}),
    # lists with same string in both, at different positions, result in duplicates keeping their positions
    (["a", "b", "c", "d"], ["d", "e", "f"], ["d", "e", "f", "d"]),
    # lists with same dict in both result in a list with one instance of that dict
    ([{"b": "c"}], [{"b": "c"}], [{"b": "c"}]),
    # if dicts in lists have different values, they are not merged
    ([{"b": "c"}], [{"b": "e"}], [{"b": "e"}]),
    # if nested dicts in lists have different keys, additive behaviour
    ([{"b": "c"}], [{"d": {"e": "f"}}], [{"b": "c", "d": {"e": "f"}}]),
    # if dicts in destination list but not source, they just get added to end of source
    ([{"a": "b"}], [{"a": "b"}, {"a": "b"}, {"c": "d"}], [{"a": "b"}, {"a": "b"}, {"c": "d"}]),
    # merge a dict with a null object returns that dict (does not work the other way round)
    ({"a": {"b": "c"}}, None, {"a": {"b": "c"}}),
    # double nested dicts, new adds new Boolean key: value, additive behaviour
    ({"a": {"b": {"c": "d"}}}, {"a": {"b": {"e": True}}}, {"a": {"b": {"c": "d", "e": True}}}),
    # double nested dicts, both have same key, different values, destination supercedes source
    ({"a": {"b": {"c": "d"}}}, {"a": {"b": {"c": "e"}}}, {"a": {"b": {"c": "e"}}})
])
def test_merge_jsonlike_merges_jsonlike_objects_correctly(source_object, destination_object, expected_result):
    merge_jsonlike(source_object, destination_object)
    assert source_object == expected_result


@pytest.mark.parametrize('value, significant_figures, expected_result', (
    (0, 1, 0),
    (0, 2, 0),
    (12_345, 1, 10_000),
    (12_345, 2, 12_000),
    (12_345, 3, 12_300),
    (12_345, 9, 12_345),
    (12_345.6789, 1, 10_000),
    (12_345.6789, 9, 12_345),
    (-12_345, 1, -10_000),
))
def test_round_to_significant_figures(value, significant_figures, expected_result):
    assert round_to_significant_figures(value, significant_figures) == expected_result


@pytest.mark.parametrize('datetime_string, financial_year', (
    ('2021-01-01T00:00:00+00:00', 2020),  # Start of 2021
    ('2021-03-31T22:59:59+00:00', 2020),  # One minute before midnight (BST)
    ('2021-03-31T23:00:00+00:00', 2021),  # Midnight (BST)
    ('2021-12-12T12:12:12+01:00', 2021),  # Later in the year
))
def test_get_financial_year(datetime_string, financial_year):
    with freeze_time(datetime_string):
        assert get_current_financial_year() == financial_year

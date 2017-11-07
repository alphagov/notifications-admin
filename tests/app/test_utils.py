from pathlib import Path
from io import StringIO
from collections import OrderedDict
from csv import DictReader

from freezegun import freeze_time
import pytest

from app.utils import (
    email_safe,
    generate_notifications_csv,
    generate_previous_dict,
    generate_next_dict,
    Spreadsheet,
    get_letter_timings,
    get_cdn_domain,
    unescape_string,
)


def _get_notifications_csv(
    service_id,
    page=1,
    row_number=1,
    recipient='foo@bar.com',
    template_name='foo',
    template_type='sms',
    job_name='bar.csv',
    status='Delivered',
    created_at='Thursday 19 April at 12:00',
    rows=1,
    with_links=False
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
            "row_number": row_number,
            "recipient": recipient,
            "template_name": template_name,
            "template_type": template_type,
            "job_name": job_name,
            "status": status,
            "created_at": created_at
        } for i in range(rows)],
        'total': rows,
        'page_size': 50,
        'links': links
    }
    return data


@pytest.fixture(scope='function')
def _get_notifications_csv_mock(
    mocker,
    api_user_active
):
    return mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=_get_notifications_csv
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


def test_generate_notifications_csv_returns_correct_csv_file(_get_notifications_csv_mock):
    csv_content = generate_notifications_csv(service_id='1234')
    csv_file = DictReader(StringIO('\n'.join(csv_content)))
    assert csv_file.fieldnames == ['Row number', 'Recipient', 'Template', 'Type', 'Job', 'Status', 'Time']


def test_generate_notifications_csv_only_calls_once_if_no_next_link(_get_notifications_csv_mock):
    list(generate_notifications_csv(service_id='1234'))

    assert _get_notifications_csv_mock.call_count == 1


def test_generate_notifications_csv_calls_twice_if_next_link(mocker):
    service_id = '1234'
    response_with_links = _get_notifications_csv(service_id, rows=7, with_links=True)
    response_with_no_links = _get_notifications_csv(service_id, rows=3, with_links=False)

    mock_get_notifications = mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=[
            response_with_links,
            response_with_no_links,
        ]
    )

    csv_content = generate_notifications_csv(service_id=service_id)
    csv = DictReader(StringIO('\n'.join(csv_content)))

    assert len(list(csv)) == 10
    assert mock_get_notifications.call_count == 2
    # mock_calls[0][2] is the kwargs from first call
    assert mock_get_notifications.mock_calls[0][2]['page'] == 1
    assert mock_get_notifications.mock_calls[1][2]['page'] == 2


@freeze_time('2017-07-14 14:59:59')  # Friday, before print deadline
@pytest.mark.parametrize('upload_time, expected_print_time, is_printed, expected_earliest, expected_latest', [

    # BST
    # ==================================================================
    #  First thing Monday
    (
        '2017-07-10 00:00:01',
        'Tuesday 15:00',
        True,
        'Thursday 2017-07-13',
        'Friday 2017-07-14'
    ),
    #  Monday at 16:59 BST
    (
        '2017-07-10 15:59:59',
        'Tuesday 15:00',
        True,
        'Thursday 2017-07-13',
        'Friday 2017-07-14'
    ),
    #  Monday at 17:00 BST
    (
        '2017-07-10 16:00:01',
        'Wednesday 15:00',
        True,
        'Friday 2017-07-14',
        'Saturday 2017-07-15'
    ),
    #  Tuesday before 17:00 BST
    (
        '2017-07-11 12:00:00',
        'Wednesday 15:00',
        True,
        'Friday 2017-07-14',
        'Saturday 2017-07-15'
    ),
    #  Wednesday before 17:00 BST
    (
        '2017-07-12 12:00:00',
        'Thursday 15:00',
        True,
        'Saturday 2017-07-15',
        'Monday 2017-07-17'
    ),
    #  Thursday before 17:00 BST
    (
        '2017-07-13 12:00:00',
        'Friday 15:00',
        True,  # WRONG
        'Monday 2017-07-17',
        'Tuesday 2017-07-18'
    ),
    #  Friday anytime
    (
        '2017-07-14 00:00:00',
        'Monday 15:00',
        False,
        'Wednesday 2017-07-19',
        'Thursday 2017-07-20'
    ),
    (
        '2017-07-14 12:00:00',
        'Monday 15:00',
        False,
        'Wednesday 2017-07-19',
        'Thursday 2017-07-20'
    ),
    (
        '2017-07-14 22:00:00',
        'Monday 15:00',
        False,
        'Wednesday 2017-07-19',
        'Thursday 2017-07-20'
    ),
    #  Saturday anytime
    (
        '2017-07-14 12:00:00',
        'Monday 15:00',
        False,
        'Wednesday 2017-07-19',
        'Thursday 2017-07-20'
    ),
    #  Sunday before 1700 BST
    (
        '2017-07-15 15:59:59',
        'Monday 15:00',
        False,
        'Wednesday 2017-07-19',
        'Thursday 2017-07-20'
    ),
    #  Sunday after 17:00 BST
    (
        '2017-07-16 16:00:01',
        'Tuesday 15:00',
        False,
        'Thursday 2017-07-20',
        'Friday 2017-07-21'
    ),

    # GMT
    # ==================================================================
    #  Monday at 16:59 GMT
    (
        '2017-01-02 16:59:59',
        'Tuesday 15:00',
        True,
        'Thursday 2017-01-05',
        'Friday 2017-01-06',
    ),
    #  Monday at 17:00 GMT
    (
        '2017-01-02 17:00:01',
        'Wednesday 15:00',
        True,
        'Friday 2017-01-06',
        'Saturday 2017-01-07',
    ),

])
def test_get_estimated_delivery_date_for_letter(
    upload_time,
    expected_print_time,
    is_printed,
    expected_earliest,
    expected_latest,
):
    timings = get_letter_timings(upload_time)
    assert timings.printed_by.strftime('%A %H:%M') == expected_print_time
    assert timings.is_printed == is_printed
    assert timings.earliest_delivery.strftime('%A %Y-%m-%d') == expected_earliest
    assert timings.latest_delivery.strftime('%A %Y-%m-%d') == expected_latest


def test_get_cdn_domain_on_localhost(client, mocker):
    mocker.patch.dict('app.current_app.config', values={'ADMIN_BASE_URL': 'http://localhost:6012'})
    domain = get_cdn_domain()
    assert domain == 'static-logos.notify.tools'


def test_get_cdn_domain_on_non_localhost(client, mocker):
    mocker.patch.dict('app.current_app.config', values={'ADMIN_BASE_URL': 'https://some.admintest.com'})
    domain = get_cdn_domain()
    assert domain == 'static-logos.admintest.com'


@pytest.mark.parametrize('raw, expected', [
    (
        '😬',
        '😬',
    ),
    (
        '1\\n2',
        '1\n2',
    ),
    (
        '\\\'"\\\'',
        '\'"\'',
    ),
    (
        """

        """,
        """

        """,
    ),
    (
        '\x79 \\x79 \\\\x79',  # we should never see the middle one
        'y y \\x79',
    ),
])
def test_unescape_string(raw, expected):
    assert unescape_string(raw) == expected

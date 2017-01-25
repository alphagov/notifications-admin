from pathlib import Path
from io import StringIO
from csv import DictReader

import pytest
from freezegun import freeze_time

from app.utils import (
    email_safe,
    generate_notifications_csv,
    generate_previous_dict,
    generate_next_dict,
    Spreadsheet,
    format_notification_for_csv
)

from tests import notification_json, single_notification_json, template_json


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


@pytest.mark.parametrize(
    "status, template_type, expected_status",
    [
        ('temporary-failure', 'email', 'Inbox not accepting messages right now'),
        ('permanent-failure', 'email', 'Email address doesn’t exist'),
        ('temporary-failure', 'sms', 'Phone not accepting messages right now'),
        ('permanent-failure', 'sms', 'Phone number doesn’t exist')
    ]
)
def test_format_notification_for_csv_formats_status(
    status,
    template_type,
    expected_status
):
    json_row = single_notification_json(
        '1234',
        template=template_json(service_id='1234', id_='5678', type_=template_type),
        status=status
    )
    csv_line = format_notification_for_csv(json_row)

    assert csv_line['Status'] == expected_status


@freeze_time("2016-01-01 15:09:00.061258")
def test_format_notification_for_csv_formats_time():
    json_row = single_notification_json('1234')

    csv_line = format_notification_for_csv(json_row)

    assert csv_line['Time'] == 'Friday 01 January 2016 at 15:09'


def test_generate_notifications_csv_returns_correct_csv_file(mock_get_notifications):
    csv_content = generate_notifications_csv(service_id='1234')

    csv_file = DictReader(StringIO('\n'.join(csv_content)))
    assert csv_file.fieldnames == ['Row number', 'Recipient', 'Template', 'Type', 'Job', 'Status', 'Time']


def test_generate_notifications_csv_only_calls_once_if_no_next_link(mock_get_notifications):
    list(generate_notifications_csv(service_id='1234'))

    assert mock_get_notifications.call_count == 1


def test_generate_notifications_csv_calls_twice_if_next_link(mocker):
    service_id = '1234'
    response_with_links = notification_json(service_id, rows=5, with_links=True)
    response_with_no_links = notification_json(service_id, rows=2, with_links=False)
    mock_get_notifications = mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=[
            response_with_links,
            response_with_no_links,
        ]
    )

    csv_content = generate_notifications_csv(service_id=service_id)
    csv = DictReader(StringIO('\n'.join(csv_content)))

    assert len(list(csv)) == 7
    assert mock_get_notifications.call_count == 2
    # mock_calls[0][2] is the kwargs from first call
    assert mock_get_notifications.mock_calls[0][2]['page'] == 1
    assert mock_get_notifications.mock_calls[1][2]['page'] == 2


@pytest.mark.parametrize('row_number, expected_result', [
    (None, ''),
    (0, '1'),
    (1, '2'),
    (300, '301')
])
def test_generate_notifications_csv_formats_row_number_correctly(mocker, row_number, expected_result):
    service_id = '1234'
    response_with_job_row_zero = notification_json(service_id, rows=1, with_links=True, job_row_number=row_number)
    mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=[
            response_with_job_row_zero
        ]
    )

    csv_content = generate_notifications_csv(service_id=service_id)
    csv = DictReader(StringIO('\n'.join(csv_content)))
    csv_rows = list(csv)

    assert len(csv_rows) == 1
    assert csv_rows[0].get('Row number') == expected_result


def normalize_spaces(string):
    return ' '.join(string.split())

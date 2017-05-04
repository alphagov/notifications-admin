from pathlib import Path
from io import StringIO
from csv import DictReader

import pytest

from app.utils import (
    email_safe,
    generate_notifications_csv,
    generate_previous_dict,
    generate_next_dict,
    Spreadsheet
)

from tests import notification_json, single_notification_json


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


def normalize_spaces(string):
    return ' '.join(string.split())

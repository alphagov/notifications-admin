from pathlib import Path
from io import StringIO
from csv import DictReader

import pytest
from freezegun import freeze_time

from app.utils import email_safe, generate_notifications_csv, generate_previous_dict, generate_next_dict, Spreadsheet


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


@pytest.mark.parametrize(
    "status, template_type, expected_status",
    [
        ('sending', None, 'Sending'),
        ('delivered', None, 'Delivered'),
        ('failed', None, 'Failed'),
        ('technical-failure', None, 'Technical failure'),
        ('temporary-failure', 'email', 'Inbox not accepting messages right now'),
        ('permanent-failure', 'email', 'Email address doesn’t exist'),
        ('temporary-failure', 'sms', 'Phone not accepting messages right now'),
        ('permanent-failure', 'sms', 'Phone number doesn’t exist')
    ]
)
@freeze_time("2016-01-01 15:09:00.061258")
def test_generate_csv_from_notifications(
    app_,
    service_one,
    active_user_with_permissions,
    mock_get_notifications,
    status,
    template_type,
    expected_status
):
    with app_.test_request_context():
        csv_content = generate_notifications_csv(
            mock_get_notifications(
                service_one['id'],
                rows=1,
                set_template_type=template_type,
                set_status=status
            )['notifications']
        )
    for row in DictReader(StringIO(next(csv_content))):
        assert row['Time'] == 'Friday 01 January 2016 at 15:09'
        assert row['Status'] == expected_status


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

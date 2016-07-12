import pytest
from io import StringIO
from app.utils import email_safe, generate_notifications_csv
from csv import DictReader
from freezegun import freeze_time


def test_email_safe_return_dot_separated_email_domain():
    test_name = 'SOME service  with+stuff+ b123'
    expected = 'some.service.withstuff.b123'
    actual = email_safe(test_name)
    assert actual == expected


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
@freeze_time("2016-01-01 11:09:00.061258")
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

    for row in DictReader(StringIO(csv_content)):
        assert row['Time'] == 'Friday 01 January 2016 at 11:09'
        assert row['Status'] == expected_status

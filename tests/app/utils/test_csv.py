from collections import namedtuple
from csv import DictReader
from io import StringIO
from unittest.mock import Mock

import pytest
from notifications_python_client.errors import HTTPError

from app.utils.csv import generate_notifications_csv, get_errors_for_csv
from tests import sample_uuid
from tests.conftest import fake_uuid


def _get_notifications_csv(
    row_number=1,
    recipient="foo@bar.com",
    template_name="foo",
    template_type="sms",
    job_name="bar.csv",
    status="Delivered",
    created_at="2023-04-19 12:00:00",
    rows=1,
    job_id=fake_uuid,
    created_by_name=None,
    created_by_email_address=None,
    api_key_name=None,
    page_size=50,
):
    def _get(service_id, page=1, job_id=None, template_type=template_type, page_size=page_size):
        links = {}
        data = {
            "notifications": [
                {
                    "id": sample_uuid(),
                    "row_number": (row_number + i) if row_number else "",
                    "to": recipient,
                    "recipient": recipient,
                    "client_reference": "ref 1234",
                    "template_name": template_name,
                    "template_type": template_type,
                    "template": {"name": template_name, "template_type": template_type},
                    "job_name": job_name,
                    "status": status,
                    "created_at": created_at,
                    "updated_at": None,
                    "created_by_name": created_by_name,
                    "created_by_email_address": created_by_email_address,
                    "api_key_name": api_key_name,
                }
                for i in range(rows)
            ],
            "total": rows,
            "page_size": page_size,
            "links": links,
        }

        return data

    return _get


@pytest.fixture(scope="function")
def _get_notifications_csv_mock(
    mocker,
    api_user_active,
):
    return mocker.patch("app.models.notification.NotificationsForCSV._get_items", side_effect=_get_notifications_csv())


@pytest.mark.parametrize(
    "created_by_name, api_key_name, expected_content",
    [
        (
            None,
            "my-key-name",
            [
                "Recipient,Reference,Template,Type,Sent by,Sent by email,Job,Status,Time,API key name\n",
                "foo@bar.com,ref 1234,foo,sms,,sender@email.gov.uk,,Delivered,2023-04-19 12:00:00,my-key-name\r\n",
            ],
        ),
        (
            "Anne Example",
            None,
            [
                "Recipient,Reference,Template,Type,Sent by,Sent by email,Job,Status,Time,API key name\n",
                "foo@bar.com,ref 1234,foo,sms,Anne Example,sender@email.gov.uk,,Delivered,2023-04-19 12:00:00,\r\n",
            ],
        ),
    ],
)
def test_generate_notifications_csv_without_job(
    notify_admin,
    mocker,
    created_by_name,
    api_key_name,
    expected_content,
):
    mocker.patch(
        "app.models.notification.NotificationsForCSV._get_items",
        side_effect=_get_notifications_csv(
            created_by_name=created_by_name,
            created_by_email_address="sender@email.gov.uk",
            job_id=None,
            job_name=None,
            api_key_name=api_key_name,
            row_number="",
        ),
    )
    assert (
        list(
            generate_notifications_csv(
                service_id=fake_uuid,
                page_size=3,
            )
        )
        == expected_content
    )


@pytest.mark.parametrize(
    "original_file_contents, expected_column_headers, expected_1st_row",
    [
        (
            """
            phone_number
            07700900123
        """,
            ["Row number", "phone_number", "Template", "Type", "Job", "Status", "Time"],
            ["1", "07700900123", "foo", "sms", "bar.csv", "Delivered", "2023-04-19 12:00:00"],
        ),
        (
            """
            phone_number, a, b, c
            07700900123,  🐜,🐝,🦀
        """,
            ["Row number", "phone_number", "a", "b", "c", "Template", "Type", "Job", "Status", "Time"],
            ["1", "07700900123", "🐜", "🐝", "🦀", "foo", "sms", "bar.csv", "Delivered", "2023-04-19 12:00:00"],
        ),
        (
            """
            "phone_number", "a", "b", "c"
            "07700900123","🐜,🐜","🐝,🐝","🦀"
        """,
            ["Row number", "phone_number", "a", "b", "c", "Template", "Type", "Job", "Status", "Time"],
            ["1", "07700900123", "🐜,🐜", "🐝,🐝", "🦀", "foo", "sms", "bar.csv", "Delivered", "2023-04-19 12:00:00"],
        ),
    ],
)
def test_generate_notifications_csv_returns_correct_csv_file(
    notify_admin,
    mocker,
    _get_notifications_csv_mock,
    original_file_contents,
    expected_column_headers,
    expected_1st_row,
):
    mocker.patch(
        "app.s3_client.s3_csv_client.s3download",
        return_value=original_file_contents,
    )
    csv_content = generate_notifications_csv(service_id="1234", job_id=fake_uuid, template_type="sms", page_size=3)
    csv_file = DictReader(StringIO("\n".join(csv_content)))
    assert csv_file.fieldnames == expected_column_headers
    assert next(csv_file) == dict(zip(expected_column_headers, expected_1st_row, strict=True))


def test_generate_notifications_csv_only_calls_once_if_notifications_batch_smaller_than_page_size(
    notify_admin,
    _get_notifications_csv_mock,
):
    # our mock returns 1 notification by default, but the page fits 3 notifications - so we know there are no older
    # unpulled ones
    list(generate_notifications_csv(service_id="1234", page_size=3))

    assert _get_notifications_csv_mock.call_count == 1


@pytest.mark.parametrize("job_id", ["some", None])
def test_generate_notifications_csv_calls_twice_if_notifications_batch_equals_page_size(
    notify_admin,
    mocker,
    job_id,
):
    mocker.patch(
        "app.s3_client.s3_csv_client.s3download",
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
        """,
    )

    service_id = "1234"
    response_1 = _get_notifications_csv(rows=7)
    response_2 = _get_notifications_csv(rows=3, row_number=8)

    mock_get_notifications = mocker.patch(
        "app.models.notification.NotificationsForCSV._get_items",
        side_effect=[
            response_1(service_id),
            response_2(service_id),
        ],
    )

    csv_content = generate_notifications_csv(
        service_id=service_id,
        job_id=job_id or fake_uuid,
        template_type="sms",
        page_size=7,
    )
    csv = list(DictReader(StringIO("\n".join(csv_content))))

    assert len(csv) == 10
    assert csv[0]["phone_number"] == "07700900000"
    assert csv[9]["phone_number"] == "07700900009"
    assert mock_get_notifications.call_count == 2

    # mock_calls[0][2] is the kwargs from first call
    assert mock_get_notifications.mock_calls[0][2]["page"] == 1
    assert not mock_get_notifications.mock_calls[0][2].get("older_than")

    assert mock_get_notifications.mock_calls[1][2]["page"] == 2
    assert mock_get_notifications.mock_calls[1][2]["older_than"] == sample_uuid()


@pytest.mark.parametrize("job_id", ["some", None])
def test_generate_notifications_csv_when_rows_number_divisible_by_page_size(
    notify_admin,
    mocker,
    job_id,
):
    mocker.patch(
        "app.s3_client.s3_csv_client.s3download",
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
        """,
    )

    service_id = "1234"
    response_1 = _get_notifications_csv(rows=5)
    response_2 = _get_notifications_csv(rows=5, row_number=6)

    mock_get_notifications = mocker.patch(
        "app.models.notification.NotificationsForCSV._get_items",
        side_effect=[response_1(service_id), response_2(service_id), HTTPError(response=Mock(status_code=404))],
    )

    csv_content = generate_notifications_csv(
        service_id=service_id,
        job_id=job_id or fake_uuid,
        template_type="sms",
        page_size=5,
    )
    csv = list(DictReader(StringIO("\n".join(csv_content))))

    assert len(csv) == 10
    assert csv[0]["phone_number"] == "07700900000"
    assert csv[9]["phone_number"] == "07700900009"
    assert mock_get_notifications.call_count == 3

    # mock_calls[0][2] is the kwargs from first call
    assert mock_get_notifications.mock_calls[0][2]["page"] == 1
    assert not mock_get_notifications.mock_calls[0][2].get("older_than")

    assert mock_get_notifications.mock_calls[1][2]["page"] == 2
    assert mock_get_notifications.mock_calls[1][2]["older_than"] == sample_uuid()

    assert mock_get_notifications.mock_calls[2][2]["page"] == 3


MockRecipients = namedtuple(
    "RecipientCSV",
    [
        "rows_with_bad_recipients",
        "rows_with_missing_data",
        "rows_with_message_too_long",
        "rows_with_empty_message",
        "rows_with_bad_qr_codes",
    ],
)


@pytest.mark.parametrize(
    "rows_with_bad_recipients, rows_with_missing_data, "
    "rows_with_message_too_long, rows_with_empty_message, rows_with_bad_qr_codes, template_type, expected_errors",
    [
        ([], [], [], [], [], "sms", []),
        ({2}, [], [], [], [], "sms", ["fix 1 phone number"]),
        ({2, 4, 6}, [], [], [], [], "sms", ["fix 3 phone numbers"]),
        ({1}, [], [], [], [], "email", ["fix 1 email address"]),
        ({2, 4, 6}, [], [], [], [], "email", ["fix 3 email addresses"]),
        ({2}, [], [], [], [], "letter", ["fix 1 address"]),
        ({2, 4}, [], [], [], [], "letter", ["fix 2 addresses"]),
        ({2}, {3}, [], [], [], "sms", ["fix 1 phone number", "enter missing data in 1 row"]),
        ({2, 4, 6, 8}, {3, 6, 9, 12}, [], [], [], "sms", ["fix 4 phone numbers", "enter missing data in 4 rows"]),
        ({}, {}, {3}, [], [], "sms", ["shorten the message in 1 row"]),
        ({}, {}, {3, 12}, [], [], "sms", ["shorten the messages in 2 rows"]),
        ({}, {}, {}, {2}, [], "sms", ["check you have content for the empty message in 1 row"]),
        ({}, {}, {}, {2, 4, 8}, [], "sms", ["check you have content for the empty messages in 3 rows"]),
        ([], [], [], [], {2}, "letter", ["enter fewer characters for the QR code links in 1 row"]),
        ([], [], [], [], {2, 4}, "letter", ["enter fewer characters for the QR code links in 2 rows"]),
    ],
)
def test_get_errors_for_csv(
    rows_with_bad_recipients,
    rows_with_missing_data,
    rows_with_message_too_long,
    rows_with_empty_message,
    rows_with_bad_qr_codes,
    template_type,
    expected_errors,
):
    assert (
        get_errors_for_csv(
            MockRecipients(
                rows_with_bad_recipients,
                rows_with_missing_data,
                rows_with_message_too_long,
                rows_with_empty_message,
                rows_with_bad_qr_codes,
            ),
            template_type,
        )
        == expected_errors
    )

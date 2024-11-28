import time

from notifications_utils.recipients import RecipientCSV

from app.formatters import recipient_count
from app.models.notification import NotificationsForCSV
from app.models.spreadsheet import Spreadsheet
from app.utils.templates import get_sample_template


def get_errors_for_csv(recipients, template_type):
    errors = []

    if any(recipients.rows_with_bad_recipients):
        number_of_bad_recipients = len(list(recipients.rows_with_bad_recipients))
        errors.append(f"fix {recipient_count(number_of_bad_recipients, template_type)}")

    if any(recipients.rows_with_missing_data):
        number_of_rows_with_missing_data = len(list(recipients.rows_with_missing_data))
        if 1 == number_of_rows_with_missing_data:
            errors.append("enter missing data in 1 row")
        else:
            errors.append(f"enter missing data in {number_of_rows_with_missing_data} rows")

    if any(recipients.rows_with_message_too_long):
        number_of_rows_with_message_too_long = len(list(recipients.rows_with_message_too_long))
        if 1 == number_of_rows_with_message_too_long:
            errors.append("shorten the message in 1 row")
        else:
            errors.append(f"shorten the messages in {number_of_rows_with_message_too_long} rows")

    if any(recipients.rows_with_empty_message):
        number_of_rows_with_empty_message = len(list(recipients.rows_with_empty_message))
        if 1 == number_of_rows_with_empty_message:
            errors.append("check you have content for the empty message in 1 row")
        else:
            errors.append(f"check you have content for the empty messages in {number_of_rows_with_empty_message} rows")

    if any(recipients.rows_with_bad_qr_codes):
        number_of_rows_with_bad_qr_codes = len(list(recipients.rows_with_bad_qr_codes))
        if 1 == number_of_rows_with_bad_qr_codes:
            errors.append("enter fewer characters for the QR code links in 1 row")
        else:
            errors.append(f"enter fewer characters for the QR code links in {number_of_rows_with_bad_qr_codes} rows")

    return errors


def generate_notifications_csv(**kwargs):
    from app.s3_client.s3_csv_client import s3download

    if "page" not in kwargs:
        kwargs["page"] = 1

    if kwargs.get("job_id"):
        original_file_contents = s3download(kwargs["service_id"], kwargs["job_id"])
        original_upload = RecipientCSV(
            original_file_contents,
            template=get_sample_template(kwargs["template_type"]),
        )
        original_column_headers = original_upload.column_headers
        fieldnames = ["Row number"] + original_column_headers + ["Template", "Type", "Job", "Status", "Time"]
    else:
        fieldnames = [
            "Recipient",
            "Reference",
            "Template",
            "Type",
            "Sent by",
            "Sent by email",
            "Job",
            "Status",
            "Time",
            "API key name",
        ]

    while True:
        time.sleep(40)
        notifications_batch = NotificationsForCSV(**kwargs)

        for notification in notifications_batch:
            if kwargs.get("job_id"):
                values = (
                    [
                        notification.row_number,
                    ]
                    + [
                        original_upload[notification.row_number - 1].get(header).data
                        for header in original_column_headers
                    ]
                    + [
                        notification.template_name,
                        notification.template_type,
                        notification.job_name,
                        notification.status,
                        notification.created_at,
                    ]
                )
            else:
                values = [
                    # the recipient for precompiled letters is the full address block
                    notification.recipient.splitlines()[0].lstrip().rstrip(" ,"),
                    notification.client_reference,
                    notification.template_name,
                    notification.template_type,
                    notification.created_by_name or "",
                    notification.created_by_email_address or "",
                    notification.job_name or "",
                    notification.status,
                    notification.created_at,
                    notification.api_key_name or "",
                ]
            return Spreadsheet.from_rows([fieldnames] + [map(str, values)]).as_csv_data

        if len(notifications_batch) == kwargs["page_size"]:
            kwargs["page"] += 1
            kwargs["older_than"] = notifications_batch[-1].id
        else:
            return
    raise Exception("Should never reach here")

from collections import OrderedDict

from flask import render_template

from app import current_service, service_api_client
from app.main import main
from app.utils import Spreadsheet, user_has_permissions


@main.route("/services/<uuid:service_id>/returned-letters")
@user_has_permissions('view_activity')
def returned_letter_summary(service_id):
    return render_template(
        'views/returned-letter-summary.html',
        data=current_service.returned_letter_summary,
    )


@main.route("/services/<uuid:service_id>/returned-letters/<simple_date:reported_at>")
@user_has_permissions('view_activity')
def returned_letters(service_id, reported_at):

    page_size = 50
    returned_letters = service_api_client.get_returned_letters(service_id, reported_at)
    count_of_returned_letters = len(returned_letters)

    return render_template(
        'views/returned-letters.html',
        returned_letters=returned_letters[:page_size],
        reported_at=reported_at,
        more_than_one_page=(count_of_returned_letters > page_size),
        page_size=page_size,
        count_of_returned_letters=count_of_returned_letters,
    )


@main.route("/services/<uuid:service_id>/returned-letters/<simple_date:reported_at>.csv")
@user_has_permissions('view_activity')
def returned_letters_report(service_id, reported_at):
    returned_letters = service_api_client.get_returned_letters(service_id, reported_at)
    column_names = OrderedDict([
        ('notification_id', 'Notification ID'),
        ('client_reference', 'Reference'),
        ('created_at', 'Date sent'),
        ('email_address', 'Sent by'),
        ('template_name', 'Template name'),
        ('template_id', 'Template ID'),
        ('template_version', 'Template version'),
        ('original_file_name', 'Spreadsheet file name'),
        ('job_row_number', 'Spreadsheet row number'),
        ('uploaded_letter_file_name', 'Uploaded letter file name')
    ])

    # initialise with header row
    data = [[x for x in column_names.values()]]

    for row in returned_letters:
        data.append([row[key] for key in column_names.keys()])

    return Spreadsheet.from_rows(data).as_csv_data, 200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'inline; filename="{} returned letters.csv"'.format(reported_at)
    }

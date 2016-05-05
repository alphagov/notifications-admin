import csv
import io
import json
import uuid
import itertools
from contextlib import suppress

from flask import (
    request,
    render_template,
    redirect,
    url_for,
    flash,
    abort,
    session,
    current_app
)

from flask_login import login_required, current_user
from notifications_utils.template import Template
from notifications_utils.recipients import RecipientCSV, first_column_heading, validate_and_format_phone_number

from app.main import main
from app.main.forms import CsvUploadForm
from app.main.uploader import (
    s3upload,
    s3download
)
from app import job_api_client, service_api_client, current_service, user_api_client, statistics_api_client
from app.utils import user_has_permissions, get_errors_for_csv, Spreadsheet


def get_send_button_text(template_type, number_of_messages):
    if 1 == number_of_messages:
        return {
            'email': 'Send 1 email',
            'sms': 'Send 1 text message'
        }[template_type]
    else:
        return {
            'email': 'Send {} emails',
            'sms': 'Send {} text messages'
        }[template_type].format(number_of_messages)


def get_page_headings(template_type):
    return {
        'email': 'Email templates',
        'sms': 'Text message templates'
    }[template_type]


def get_example_csv_fields(column_headers, use_example_as_example, submitted_fields):
    if use_example_as_example:
        return ["example" for header in column_headers]
    elif submitted_fields:
        return [submitted_fields.get(header) for header in column_headers]
    else:
        return list(column_headers)


def get_example_csv_rows(template, use_example_as_example=True, submitted_fields=False):
    return [
        {
            'email': 'test@example.com' if use_example_as_example else current_user.email_address,
            'sms': '07700 900321' if use_example_as_example else validate_and_format_phone_number(
                current_user.mobile_number, human_readable=True
            )
        }[template.template_type]
    ] + get_example_csv_fields(template.placeholders, use_example_as_example, submitted_fields)


@main.route("/services/<service_id>/send/<template_type>", methods=['GET'])
@login_required
@user_has_permissions('view_activity',
                      'send_texts',
                      'send_emails',
                      'manage_templates',
                      'manage_api_keys',
                      admin_override=True, any_=True)
def choose_template(service_id, template_type):
    if template_type not in ['email', 'sms']:
        abort(404)

    return render_template(
        'views/templates/choose.html',
        templates=[
            Template(
                template,
                prefix=current_service['name']
            ) for template in service_api_client.get_service_templates(service_id)['data']
            if template['template_type'] == template_type
        ],
        template_type=template_type,
        page_heading=get_page_headings(template_type)
    )


@main.route("/services/<service_id>/send/<template_id>/csv", methods=['GET', 'POST'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def send_messages(service_id, template_id):
    template = Template(
        service_api_client.get_service_template(service_id, template_id)['data'],
        prefix=current_service['name']
    )

    form = CsvUploadForm()
    if form.validate_on_submit():

        if form.file.data.filename.lower().endswith('.xlsx'):
            contents = Spreadsheet.from_xlsx(form.file.data).as_csv
        elif form.file.data.filename.lower().endswith('.xls'):
            contents = Spreadsheet.from_xls(form.file.data).as_csv
        else:
            contents = Spreadsheet(form.file.data).as_csv

        try:
            upload_id = str(uuid.uuid4())
            s3upload(
                upload_id,
                service_id,
                {
                    'file_name': form.file.data.filename,
                    'data': contents
                },
                current_app.config['AWS_REGION']
            )
            session['upload_data'] = {
                "template_id": template_id,
                "original_file_name": form.file.data.filename
            }
            return redirect(url_for('.check_messages',
                                    service_id=service_id,
                                    upload_id=upload_id,
                                    template_type=template.template_type))
        except ValueError as e:
            flash('There was a problem uploading: {}'.format(form.file.data.filename))
            flash(str(e))
            return redirect(url_for('.send_messages', service_id=service_id, template_id=template_id))

    return render_template(
        'views/send.html',
        template=template,
        recipient_column=first_column_heading[template.template_type],
        example=[get_example_csv_rows(template)],
        form=form
    )


@main.route("/services/<service_id>/send/<template_id>.csv", methods=['GET'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters', 'manage_templates', any_=True)
def get_example_csv(service_id, template_id):
    template = Template(service_api_client.get_service_template(service_id, template_id)['data'])
    with io.StringIO() as output:
        writer = csv.writer(output)
        writer.writerows([
            [first_column_heading[template.template_type]] + list(template.placeholders),
            get_example_csv_rows(template)
        ])
        return output.getvalue(), 200, {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': 'inline; filename="{}.csv"'.format(template.name)
        }


@main.route("/services/<service_id>/send/<template_id>/test", methods=['GET', 'POST'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def send_test(service_id, template_id):

    template = Template(
        service_api_client.get_service_template(service_id, template_id)['data'],
        prefix=current_service['name']
    )

    if len(template.placeholders) == 0 or request.method == 'POST':
        with io.StringIO() as output:
            writer = csv.writer(output)
            writer.writerows([
                [first_column_heading[template.template_type]] + list(template.placeholders),
                get_example_csv_rows(template, use_example_as_example=False, submitted_fields=request.form)
            ])
            filedata = {
                'file_name': 'Test message',
                'data': output.getvalue()
            }
            upload_id = str(uuid.uuid4())
            s3upload(upload_id, service_id, filedata, current_app.config['AWS_REGION'])
            session['upload_data'] = {"template_id": template_id, "original_file_name": filedata['file_name']}
            return redirect(url_for(
                '.check_messages',
                upload_id=upload_id,
                service_id=service_id,
                template_type=template.template_type,
                from_test=True
            ))

    return render_template(
        'views/send-test.html',
        template=template,
        recipient_column=first_column_heading[template.template_type],
        example=[get_example_csv_rows(template, use_example_as_example=False)]
    )


@main.route("/services/<service_id>/send/<template_id>/from-api", methods=['GET'])
@login_required
def send_from_api(service_id, template_id):
    template = Template(
        service_api_client.get_service_template(service_id, template_id)['data'],
        prefix=current_service['name']
    )
    personalisation = {
        placeholder: "..." for placeholder in template.placeholders
    }
    return render_template(
        'views/send-from-api.html',
        template=template,
        personalisation=json.dumps(personalisation, indent=4) if personalisation else None
    )


@main.route("/services/<service_id>/<template_type>/check/<upload_id>", methods=['GET'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def check_messages(service_id, template_type, upload_id):

    if not session.get('upload_data'):
        return redirect(url_for('main.choose_template', service_id=service_id, template_type=template_type))

    users = user_api_client.get_users_for_service(service_id=service_id)
    statistics = statistics_api_client.get_statistics_for_service(service_id, limit_days=1)['data']
    statistics = statistics[0] if statistics else {}

    contents = s3download(service_id, upload_id)
    if not contents:
        flash('There was a problem reading your upload file')

    template = service_api_client.get_service_template(
        service_id,
        session['upload_data'].get('template_id')
    )['data']

    template = Template(
        template,
        prefix=current_service['name']
    )

    recipients = RecipientCSV(
        contents,
        template_type=template.template_type,
        placeholders=template.placeholders,
        max_initial_rows_shown=50,
        max_errors_shown=50,
        whitelist=itertools.chain.from_iterable(
            [user.mobile_number, user.email_address] for user in users
        ) if current_service['restricted'] else None
    )

    if request.args.get('from_test') and len(template.placeholders):
        back_link = url_for('.send_test', service_id=service_id, template_id=template.id)
    else:
        back_link = url_for('.send_messages', service_id=service_id, template_id=template.id)

    with suppress(StopIteration):
        template.values = next(recipients.rows)
        first_recipient = template.values.get(recipients.recipient_column_header, '')

    session['upload_data']['notification_count'] = len(list(recipients.rows))
    session['upload_data']['valid'] = not recipients.has_errors
    return render_template(
        'views/check.html',
        recipients=recipients,
        first_recipient=first_recipient,
        template=template,
        page_heading=get_page_headings(template.template_type),
        errors=get_errors_for_csv(recipients, template.template_type),
        rows_have_errors=any(recipients.rows_with_errors),
        count_of_recipients=session['upload_data']['notification_count'],
        count_of_displayed_recipients=(
            len(list(recipients.initial_annotated_rows_with_errors))
            if any(recipients.rows_with_errors) else
            len(list(recipients.initial_annotated_rows))
        ),
        original_file_name=session['upload_data'].get('original_file_name'),
        send_button_text=get_send_button_text(template.template_type, session['upload_data']['notification_count']),
        upload_id=upload_id,
        form=CsvUploadForm(),
        statistics=statistics,
        back_link=back_link
    )


@main.route("/services/<service_id>/<template_type>/check/<upload_id>", methods=['POST'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def recheck_messages(service_id, template_type, upload_id):

    if not session.get('upload_data'):
        return redirect(url_for('main.choose_template', service_id=service_id, template_type=template_type))

    return send_messages(service_id, session['upload_data'].get('template_id'))


@main.route("/services/<service_id>/start-job/<upload_id>", methods=['POST'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def start_job(service_id, upload_id):

    upload_data = session['upload_data']

    if request.files or not upload_data.get('valid'):
        # The csv was invalid, validate the csv again
        return send_messages(service_id, upload_data.get('template_id'))

    session.pop('upload_data')

    job_api_client.create_job(
        upload_id,
        service_id,
        upload_data.get('template_id'),
        upload_data.get('original_file_name'),
        upload_data.get('notification_count')
    )

    return redirect(
        url_for('main.view_job', job_id=upload_id, service_id=service_id)
    )

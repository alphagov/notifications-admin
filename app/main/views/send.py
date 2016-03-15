import csv
import io
import uuid
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
from utils.template import Template
from utils.recipients import RecipientCSV, first_column_heading

from app.main import main
from app.main.forms import CsvUploadForm
from app.main.uploader import (
    s3upload,
    s3download
)
from app.main.dao import templates_dao
from app.main.dao import services_dao
from app import job_api_client
from app.utils import user_has_permissions, get_errors_for_csv


send_messages_page_headings = {
    'email': 'Send emails',
    'sms': 'Send text messages'
}


manage_templates_page_headings = {
    'email': 'Email templates',
    'sms': 'Text message templates'
}


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
    # User has manage_service role
    if current_user.has_permissions(['send_texts', 'send_emails', 'send_letters']):
        return send_messages_page_headings[template_type]
    else:
        return manage_templates_page_headings[template_type]


@main.route("/services/<service_id>/send/letters", methods=['GET'])
def letters_stub(service_id):
    return render_template(
        'views/letters.html', service_id=service_id
    )


@main.route("/services/<service_id>/send/<template_type>", methods=['GET'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters', 'manage_templates', or_=True)
def choose_template(service_id, template_type):

    service = services_dao.get_service_by_id_or_404(service_id)

    if template_type not in ['email', 'sms']:
        abort(404)
    jobs = job_api_client.get_job(service_id)['data']

    return render_template(
        'views/choose-template.html',
        templates=[
            Template(
                template,
                prefix=service['name']
            ) for template in templates_dao.get_service_templates(service_id)['data']
            if template['template_type'] == template_type
        ],
        template_type=template_type,
        page_heading=get_page_headings(template_type),
        service=service,
        has_jobs=len(jobs),
        service_id=service_id
    )


@main.route("/services/<service_id>/send/<int:template_id>", methods=['GET', 'POST'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def send_messages(service_id, template_id):

    form = CsvUploadForm()
    if form.validate_on_submit():
        try:
            upload_id = str(uuid.uuid4())
            s3upload(
                upload_id,
                service_id,
                {
                    'file_name': form.file.data.filename,
                    'data': form.file.data.getvalue().decode('utf-8')
                },
                current_app.config['AWS_REGION']
            )
            session['upload_data'] = {
                "template_id": template_id,
                "original_file_name": form.file.data.filename
            }
            return redirect(url_for('.check_messages',
                                    service_id=service_id,
                                    upload_id=upload_id))
        except ValueError as e:
            flash('There was a problem uploading: {}'.format(form.file.data.filename))
            flash(str(e))
            return redirect(url_for('.send_messages', service_id=service_id, template_id=template_id))

    service = services_dao.get_service_by_id_or_404(service_id)
    template = Template(
        templates_dao.get_service_template_or_404(service_id, template_id)['data'],
        prefix=service['name']
    )

    return render_template(
        'views/send.html',
        template=template,
        recipient_column=first_column_heading[template.template_type],
        form=form,
        service=service,
        service_id=service_id
    )


@main.route("/services/<service_id>/send/<template_id>.csv", methods=['GET'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters', 'manage_templates', or_=True)
def get_example_csv(service_id, template_id):
    template = Template(templates_dao.get_service_template_or_404(service_id, template_id)['data'])
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [first_column_heading[template.template_type]] +
        list(template.placeholders)
    )
    writer.writerow([
        {
            'email': current_user.email_address,
            'sms': current_user.mobile_number
        }[template.template_type]
    ] + _get_fake_personalisation(template.placeholders))
    return output.getvalue(), 200, {'Content-Type': 'text/csv; charset=utf-8'}


@main.route("/services/<service_id>/send/<template_id>/to-self", methods=['GET'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def send_message_to_self(service_id, template_id):
    template = Template(templates_dao.get_service_template_or_404(service_id, template_id)['data'])
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [first_column_heading[template.template_type]] +
        list(template.placeholders)
    )
    if template.template_type == 'sms':
        writer.writerow(
            [current_user.mobile_number] + _get_fake_personalisation(template.placeholders)
        )
    if template.template_type == 'email':
        writer.writerow(
            [current_user.email_address] + _get_fake_personalisation(template.placeholders)
        )

    filedata = {
        'file_name': 'Test run',
        'data': output.getvalue()
    }
    upload_id = str(uuid.uuid4())
    s3upload(upload_id, service_id, filedata, current_app.config['AWS_REGION'])
    session['upload_data'] = {"template_id": template_id, "original_file_name": filedata['file_name']}

    return redirect(url_for('.check_messages',
                            service_id=service_id,
                            upload_id=upload_id))


@main.route("/services/<service_id>/check/<upload_id>", methods=['GET'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def check_messages(service_id, upload_id):

    service = services_dao.get_service_by_id_or_404(service_id)

    contents = s3download(service_id, upload_id)
    if not contents:
        flash('There was a problem reading your upload file')

    template = templates_dao.get_service_template_or_404(
        service_id,
        session['upload_data'].get('template_id')
    )['data']

    template = Template(
        template,
        prefix=service['name'] if template['template_type'] == 'sms' else ''
    )

    recipients = RecipientCSV(
        contents,
        template_type=template.template_type,
        placeholders=template.placeholders,
        max_initial_rows_shown=15,
        max_errors_shown=15
    )

    with suppress(StopIteration):
        template.values = next(recipients.rows)

    session['upload_data']['notification_count'] = len(list(recipients.rows))
    session['upload_data']['valid'] = not recipients.has_errors

    return render_template(
        'views/check.html',
        recipients=recipients,
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
        service_id=service_id,
        service=service,
        form=CsvUploadForm()
    )


@main.route("/services/<service_id>/check/<upload_id>", methods=['POST'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def start_job(service_id, upload_id):

    upload_data = session['upload_data']
    services_dao.get_service_by_id_or_404(service_id)

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
        url_for('main.view_job', service_id=service_id, job_id=upload_id)
    )


def _get_fake_personalisation(placeholders):
    return [
        "{} 1".format(header) for header in placeholders
    ]

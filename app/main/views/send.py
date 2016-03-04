import csv
import io
import uuid

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
from notifications_python_client.errors import HTTPError
from utils.template import Template, NeededByTemplateError, NoPlaceholderForDataError

from app.main import main
from app.main.forms import CsvUploadForm
from app.main.uploader import (
    s3upload,
    s3download
)
from app.main.dao import templates_dao
from app.main.dao import services_dao
from app import job_api_client
from app.utils import (
    validate_recipient, validate_header_row, InvalidPhoneError, InvalidEmailError, user_has_permissions,
    InvalidHeaderError)
from utils.process_csv import first_column_heading


send_messages_page_headings = {
    'email': 'Send emails',
    'sms': 'Send text messages'
}


manage_templates_page_headings = {
    'email': 'Manage templates',
    'sms': 'Manage templates'
}


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
    try:
        jobs = job_api_client.get_job(service_id)['data']
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e
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
            csv_file = form.file
            filedata = _get_filedata(csv_file)
            upload_id = str(uuid.uuid4())
            s3upload(upload_id, service_id, filedata, current_app.config['AWS_REGION'])
            session['upload_data'] = {"template_id": template_id, "original_file_name": filedata['file_name']}
            return redirect(url_for('.check_messages',
                                    service_id=service_id,
                                    upload_id=upload_id))
        except ValueError as e:
            flash('There was a problem uploading: {}'.format(csv_file.data.filename))
            flash(str(e))
            return redirect(url_for('.send_messages', service_id=service_id, template_id=template_id))

    service = services_dao.get_service_by_id_or_404(service_id)
    template = Template(
        templates_dao.get_service_template_or_404(service_id, template_id)['data'],
        prefix=service['name']
    )
    recipient_column = first_column_heading[template.template_type]

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
    ] + ["test {}".format(header) for header in template.placeholders])
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
            [current_user.mobile_number] +
            ["test {}".format(header) for header in template.placeholders]
        )
    if template.template_type == 'email':
        writer.writerow(
            [current_user.email_address] +
            ["test {}".format(header) for header in template.placeholders]
        )

    filedata = {
        'file_name': 'Test run',
        'data': output.getvalue().splitlines()
    }
    upload_id = str(uuid.uuid4())
    s3upload(upload_id, service_id, filedata, current_app.config['AWS_REGION'])
    session['upload_data'] = {"template_id": template_id, "original_file_name": filedata['file_name']}

    return redirect(url_for('.check_messages',
                            service_id=service_id,
                            upload_id=upload_id))


@main.route("/services/<service_id>/check/<upload_id>",
            methods=['GET', 'POST'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters')
def check_messages(service_id, upload_id):

    upload_data = session['upload_data']
    template_id = upload_data.get('template_id')
    service = services_dao.get_service_by_id_or_404(service_id)

    if request.method == 'GET':
        contents = s3download(service_id, upload_id)
        if not contents:
            flash('There was a problem reading your upload file')
        raw_template = templates_dao.get_service_template_or_404(service_id, template_id)['data']
        upload_result = _get_rows(contents, raw_template)
        session['upload_data']['notification_count'] = len(upload_result['rows'])
        template = Template(
            raw_template,
            values=upload_result['rows'][0] if upload_result['valid'] else {},
            drop_values={first_column_heading[raw_template['template_type']]},
            prefix=service['name']
        )
        return render_template(
            'views/check.html',
            upload_result=upload_result,
            template=template,
            page_heading=get_page_headings(template.template_type),
            column_headers=[first_column_heading[template.template_type]] + list(template.placeholders_as_markup),
            original_file_name=upload_data.get('original_file_name'),
            service_id=service_id,
            service=service,
            form=CsvUploadForm()
        )
    elif request.method == 'POST':
        if request.files:
            # The csv was invalid, validate the csv again
            return send_messages(service_id, template_id)

        original_file_name = upload_data.get('original_file_name')
        notification_count = upload_data.get('notification_count')
        session.pop('upload_data')
        try:
            job_api_client.create_job(upload_id, service_id, template_id, original_file_name, notification_count)
        except HTTPError as e:
            if e.status_code == 404:
                abort(404)
            else:
                raise e

        flash('We’ve started sending your messages', 'default_with_tick')
        return redirect(
            url_for('main.view_job', service_id=service_id, job_id=upload_id)
        )


def _get_filedata(file):
    import itertools
    reader = csv.reader(
        file.data.getvalue().decode('utf-8').splitlines(),
        quoting=csv.QUOTE_NONE,
        skipinitialspace=True
    )
    lines = []
    for row in reader:
        non_empties = itertools.dropwhile(lambda x: x.strip() == '', row)
        has_content = []
        for item in non_empties:
            has_content.append(item)
        if has_content:
            lines.append(row)

    if len(lines) < 2:  # must be header row and at least one data row
        message = 'The file {} contained no data'.format(file.data.filename)
        raise ValueError(message)

    content_lines = []
    for row in lines:
        content_lines.append(','.join(row).rstrip(','))
    return {'file_name': file.data.filename, 'data': content_lines}


def _get_rows(contents, raw_template):
    reader = csv.DictReader(
        contents.split('\n'),
        quoting=csv.QUOTE_NONE,
        skipinitialspace=True
    )
    valid = True
    rows = []
    for row in reader:
        rows.append(row)
        try:
            validate_recipient(
                row, template_type=raw_template['template_type']
            )
            Template(
                raw_template,
                values=row,
                drop_values={first_column_heading[raw_template['template_type']]}
            ).replaced
        except (InvalidEmailError, InvalidPhoneError, NeededByTemplateError,
                NoPlaceholderForDataError, InvalidHeaderError):
            valid = False
    return {"valid": valid, "rows": rows}

import csv
import io
import uuid
import botocore

from datetime import date

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
from werkzeug import secure_filename
from notifications_python_client.errors import HTTPError
from utils.template import Template, NeededByTemplateError, NoPlaceholderForDataError

from app.main import main
from app.main.forms import CsvUploadForm
from app.main.uploader import (
    s3upload,
    s3download
)
from app.main.dao import templates_dao
from app import job_api_client
from app.utils import (
    validate_phone_number,
    InvalidPhoneError
)


@main.route("/services/<service_id>/sms/send", methods=['GET'])
def choose_sms_template(service_id):
    try:
        jobs = job_api_client.get_job(service_id)['data']
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e
    return render_template(
        'views/choose-sms-template.html',
        templates=[
            Template(template) for template in templates_dao.get_service_templates(service_id)['data']
        ],
        has_jobs=len(jobs),
        service_id=service_id
    )


@main.route("/services/<service_id>/sms/send/<template_id>", methods=['GET', 'POST'])
@login_required
def send_sms(service_id, template_id):

    form = CsvUploadForm()
    if form.validate_on_submit():
        try:
            csv_file = form.file.data
            filedata = _get_filedata(csv_file)
            upload_id = str(uuid.uuid4())
            s3upload(upload_id, service_id, filedata, current_app.config['AWS_REGION'])
            session['upload_data'] = {"template_id": template_id, "original_file_name": filedata['file_name']}
            return redirect(url_for('.check_sms',
                                    service_id=service_id,
                                    upload_id=upload_id))
        except ValueError as e:
            flash('There was a problem uploading: {}'.format(csv_file.filename))
            flash(str(e))
            return redirect(url_for('.send_sms', service_id=service_id, template_id=template_id))

    template = Template(
        templates_dao.get_service_template_or_404(service_id, template_id)['data']
    )

    return render_template(
        'views/send-sms.html',
        template=template,
        column_headers=['phone'] + template.placeholders_as_markup,
        form=form,
        service_id=service_id
    )


@main.route("/services/<service_id>/sms/send/<template_id>.csv", methods=['GET'])
@login_required
def get_example_csv(service_id, template_id):
    template = templates_dao.get_service_template_or_404(service_id, template_id)['data']
    placeholders = list(Template(template).placeholders)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['phone'] + placeholders)
    writer.writerow([current_user.mobile_number] + ["test {}".format(header) for header in placeholders])

    return(output.getvalue(), 200, {'Content-Type': 'text/csv; charset=utf-8'})


@main.route("/services/<service_id>/sms/send/<template_id>/to-self", methods=['GET'])
@login_required
def send_sms_to_self(service_id, template_id):
    template = templates_dao.get_service_template_or_404(service_id, template_id)['data']
    placeholders = list(Template(template).placeholders)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['phone'] + placeholders)
    writer.writerow([current_user.mobile_number] + ["test {}".format(header) for header in placeholders])
    filedata = {
        'file_name': 'Test run',
        'data': output.getvalue().splitlines()
    }
    upload_id = str(uuid.uuid4())
    s3upload(upload_id, service_id, filedata, current_app.config['AWS_REGION'])
    session['upload_data'] = {"template_id": template_id, "original_file_name": filedata['file_name']}

    return redirect(url_for('.check_sms',
                            service_id=service_id,
                            upload_id=upload_id))


@main.route("/services/<service_id>/sms/check/<upload_id>",
            methods=['GET', 'POST'])
@login_required
def check_sms(service_id, upload_id):

    if request.method == 'GET':
        contents = s3download(service_id, upload_id)
        if not contents:
            flash('There was a problem reading your upload file')
        upload_data = session['upload_data']
        template_id = upload_data.get('template_id')
        raw_template = templates_dao.get_service_template_or_404(service_id, template_id)['data']
        upload_result = _get_rows(contents, raw_template)
        session['upload_data']['notification_count'] = len(upload_result['rows'])
        template = Template(
            raw_template,
            values=upload_result['rows'][0] if upload_result['valid'] else {},
            drop_values={'phone'}
        )
        return render_template(
            'views/check-sms.html',
            upload_result=upload_result,
            template=template,
            column_headers=['phone number'] + list(
                template.placeholders if upload_result['valid'] else template.placeholders_as_markup
            ),
            original_file_name=upload_data.get('original_file_name'),
            service_id=service_id,
            form=CsvUploadForm()
        )
    elif request.method == 'POST':
        upload_data = session['upload_data']
        original_file_name = upload_data.get('original_file_name')
        template_id = upload_data.get('template_id')
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
        return redirect(url_for('main.view_job',
                        service_id=service_id,
                        job_id=upload_id))


def _get_filedata(file):
    lines = file.read().decode('utf-8').splitlines()
    if len(lines) < 2:  # must be at least header and one line
        message = 'The file {} contained no data'.format(file.filename)
        raise ValueError(message)
    return {'file_name': file.filename, 'data': lines}


def _get_rows(contents, raw_template):
    reader = csv.DictReader(
        contents.split('\n'),
        lineterminator='\n',
        quoting=csv.QUOTE_NONE,
        skipinitialspace=True
    )
    valid = True
    rows = []
    for row in reader:
        rows.append(row)
        try:
            validate_phone_number(row['phone'])
            Template(raw_template, values=row, drop_values={'phone'}).replaced
        except (InvalidPhoneError, NeededByTemplateError, NoPlaceholderForDataError):
            valid = False
    return {"valid": valid, "rows": rows}

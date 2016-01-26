import csv
import re
import os

from datetime import date

from flask import (
    request,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    current_app,
    abort
)

from flask_login import login_required
from werkzeug import secure_filename

from app.main import main
from app.main.forms import CsvUploadForm
from app.main.uploader import (
    s3upload,
    s3download
)
from app.main.dao import templates_dao


@main.route("/services/<int:service_id>/sms/send", methods=['GET', 'POST'])
@login_required
def send_sms(service_id):
    form = CsvUploadForm()
    if form.validate_on_submit():
        try:
            csv_file = form.file.data
            filedata = _get_filedata(csv_file)
            upload_id = s3upload(service_id, filedata)
            return redirect(url_for('.check_sms',
                                    service_id=service_id,
                                    upload_id=upload_id))
        except ValueError as e:
            message = 'There was a problem uploading: {}'.format(
                      csv_file.filename)
            flash(message)
            flash(str(e))
            return redirect(url_for('.send_sms', service_id=service_id))

    try:
        templates = templates_dao.get_service_templates(service_id)['data']
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e

    return render_template('views/send-sms.html',
                           templates=templates,
                           form=form,
                           service_id=service_id)


@main.route("/services/<int:service_id>/sms/check/<upload_id>",
            methods=['GET', 'POST'])
@login_required
def check_sms(service_id, upload_id):
    if request.method == 'GET':
        contents = s3download(service_id, upload_id)
        upload_result = _get_numbers(contents)
        # TODO get original file name
        return render_template(
            'views/check-sms.html',
            upload_result=upload_result,
            filename='someupload_file_name.csv',
            message_template='''
                ((name)), we’ve received your ((thing)). We’ll contact you again within 1 week.
            ''',
            service_id=service_id
        )
    elif request.method == 'POST':
        # TODO create the job with template, file location etc.
        return redirect(url_for('main.view_job',
                        service_id=service_id,
                        job_id=upload_id))


def _get_filedata(file):
    lines = file.read().decode('utf-8').splitlines()
    if len(lines) < 2:  # must be at least header and one line
        message = 'The file {} contained no data'.format(file.filename)
        raise ValueError(message)
    return {'filename': file.filename, 'data': lines}


def _format_filename(filename):
    d = date.today()
    basename, extenstion = filename.split('.')
    formatted_name = '{}_{}.csv'.format(basename, d.strftime('%Y%m%d'))
    return secure_filename(formatted_name)


def _get_numbers(contents):
    pattern = re.compile(r'^\+44\s?\d{4}\s?\d{6}$')  # need better validation
    reader = csv.DictReader(
        contents.split('\n'),
        lineterminator='\n',
        quoting=csv.QUOTE_NONE)
    valid, rejects = [], []
    for i, row in enumerate(reader):
        if pattern.match(row['phone']):
            valid.append(row)
        else:
            rejects.append({"line_number": i+2, "phone": row['phone']})
    return {"valid": valid, "rejects": rejects}

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
    current_app
)

from flask_login import login_required
from werkzeug import secure_filename

from app.main import main
from app.main.forms import CsvUploadForm
from app.main.uploader import s3upload

# TODO move this to the templates directory
message_templates = [
    {
        'name': 'Reminder',
        'body': """
            Vehicle tax: Your vehicle tax for ((registration number)) expires on ((date)).
            Tax your vehicle at www.gov.uk/vehicle-tax
        """
    },
    {
        'name': 'Warning',
        'body': """
            Vehicle tax: Your vehicle tax for ((registration number)) has expired.
            Tax your vehicle at www.gov.uk/vehicle-tax
        """
    },
]


@main.route("/services/<int:service_id>/sms/send", methods=['GET', 'POST'])
@login_required
def sendsms(service_id):
    form = CsvUploadForm()
    if form.validate_on_submit():
        try:
            csv_file = form.file.data
            filename = _format_filename(csv_file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'],
                                    filename)
            csv_file.save(filepath)
            _check_file(csv_file.filename, filepath)
            return redirect(url_for('.checksms',
                                    service_id=service_id,
                                    recipients=filename))
        except (IOError, ValueError) as e:
            message = 'There was a problem uploading: {}'.format(
                      csv_file.filename)
            flash(message)
            if isinstance(e, ValueError):
                flash(str(e))
            os.remove(filepath)
            return redirect(url_for('.sendsms', service_id=service_id))

    return render_template('views/send-sms.html',
                           message_templates=message_templates,
                           form=form,
                           service_id=service_id)


@main.route("/services/<int:service_id>/sms/check", methods=['GET', 'POST'])
@login_required
def checksms(service_id):
    if request.method == 'GET':
        filename = request.args.get('recipients')
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'],
                                filename)
        upload_result = _build_upload_result(filepath)
        if upload_result.get('rejects'):
            flash('There was a problem with some of the numbers')

        return render_template(
            'views/check-sms.html',
            upload_result=upload_result,
            filename=filename,
            message_template=message_templates[0]['body'],
            service_id=service_id
        )
    elif request.method == 'POST':
        filename = request.form['recipients']
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'],
                                filename)
        try:
            upload_id = s3upload(filepath)
            # TODO when job is created record filename in job itself
            # so downstream pages can get the original filename that way
            session[upload_id] = filename
            return redirect(url_for('main.showjob', service_id=service_id, job_id=upload_id))
        except:
            flash('There as a problem saving the file')
            return redirect(url_for('.checksms', recipients=filename))


def _check_file(filename, filepath):
    if os.stat(filepath).st_size == 0:
        message = 'The file {} contained no data'.format(filename)
        raise ValueError(message)


def _format_filename(filename):
    d = date.today()
    basename, extenstion = filename.split('.')
    formatted_name = '{}_{}.csv'.format(basename, d.strftime('%Y%m%d'))
    return secure_filename(formatted_name)


def _build_upload_result(csv_file):
    try:
        file = open(csv_file, 'r')
        pattern = re.compile(r'^\+44\s?\d{4}\s?\d{6}$')
        reader = csv.DictReader(
            file.read().splitlines(),
            lineterminator='\n',
            quoting=csv.QUOTE_NONE)
        valid, rejects = [], []
        for i, row in enumerate(reader):
            if pattern.match(row['phone']):
                valid.append(row)
            else:
                rejects.append({"line_number": i+2, "phone": row['phone']})
        return {"valid": valid, "rejects": rejects}
    finally:
        file.close()

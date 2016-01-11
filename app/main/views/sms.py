import csv
import re

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

from app.main import main
from app.main.forms import CsvUploadForm

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


@main.route("/sms/send", methods=['GET', 'POST'])
@login_required
def sendsms():
    form = CsvUploadForm()
    if form.validate_on_submit():
        csv_file = form.file.data

        # in memory handing is temporary until next story to save csv file
        try:
            results = _build_upload_result(csv_file)
        except Exception as e:
            message = 'There was a problem with the file: {}'.format(
                      csv_file.filename)
            flash(message, 'error')
            return redirect(url_for('.sendsms'))

        if not results['valid'] and not results['rejects']:
            message = "The file {} contained no data".format(csv_file.filename)
            flash(message, 'error')
            return redirect(url_for('.sendsms'))

        session[csv_file.filename] = results
        return redirect(url_for('.checksms', recipients=csv_file.filename))

    return render_template('views/send-sms.html',
                           message_templates=message_templates,
                           form=form)


@main.route("/sms/check", methods=['GET', 'POST'])
@login_required
def checksms():
    if request.method == 'GET':

        recipients_filename = request.args.get('recipients')
        # upload results in session until file is persisted in next story
        upload_result = session.get(recipients_filename)
        if upload_result.get('rejects'):
            flash('There was a problem with some of the numbers', 'error')

        return render_template(
            'views/check-sms.html',
            upload_result=upload_result,
            message_template=message_templates[0]['body']
        )
    elif request.method == 'POST':
        return redirect(url_for('.showjob'))


def _build_upload_result(csv_file):
    pattern = re.compile(r'^\+44\s?\d{4}\s?\d{6}$')
    reader = csv.DictReader(
        csv_file.read().decode('utf-8').splitlines(),
        lineterminator='\n',
        quoting=csv.QUOTE_NONE)
    valid, rejects = [], []
    for i, row in enumerate(reader):
        if pattern.match(row['phone']):
            valid.append(row)
        else:
            rejects.append({"line_number": i+2, "phone": row['phone']})
    return {"valid": valid, "rejects": rejects}

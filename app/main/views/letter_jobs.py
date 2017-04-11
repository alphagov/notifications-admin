import datetime

from flask import render_template, request
from flask_login import login_required

from app import letter_jobs_client, format_datetime_24h
from app.main import main
from app.utils import user_has_permissions


@main.route("/letter-jobs", methods=['GET', 'POST'])
@login_required
@user_has_permissions(admin_override=True)
def letter_jobs():
    msg = ''
    letter_jobs_list = letter_jobs_client.get_letter_jobs()

    if request.method == 'POST':
        if len(request.form.getlist('job_id')) > 0:
            job_ids = request.form.getlist('job_id')

            response = letter_jobs_client.send_letter_jobs(job_ids)
            msg = response['response']

            for job_id in job_ids:
                job = [j for j in letter_jobs_list if job_id == j['id']][0]
                job['sending'] = 'sending'
        else:
            msg = 'No jobs selected'

    return render_template('views/letter-jobs.html', letter_jobs_list=letter_jobs_list, message=msg)

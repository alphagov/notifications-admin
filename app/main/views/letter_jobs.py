from flask import redirect, render_template, request, session, url_for
from flask_login import login_required

from app import letter_jobs_client
from app.main import main
from app.utils import user_has_permissions


@main.route("/letter-jobs", methods=['GET', 'POST'])
@login_required
@user_has_permissions(admin_override=True)
def letter_jobs():
    letter_jobs_list = letter_jobs_client.get_letter_jobs()

    if request.method == 'POST':
        if len(request.form.getlist('job_id')) > 0:
            job_ids = request.form.getlist('job_id')
            session['job_ids'] = job_ids

            response = letter_jobs_client.send_letter_jobs(job_ids)
            msg = response['response']
        else:
            msg = 'No jobs selected'

        session['msg'] = msg

        return redirect(url_for('main.letter_jobs'))

    msg = session.pop('msg', None)
    job_ids = session.pop('job_ids', None)
    if job_ids:
        for job_id in job_ids:
            job = [j for j in letter_jobs_list if job_id == j['id']][0]
            job['sending'] = 'sending'

    return render_template('views/letter-jobs.html', letter_jobs_list=letter_jobs_list, message=msg)

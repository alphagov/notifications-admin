from flask import (render_template, url_for, redirect, request, abort)
from app.main import main
from app import convert_to_boolean
from flask_login import (login_required, current_user)


@main.route("/letter-jobs", methods=['GET', 'POST'])
@login_required
def letter_jobs():
    letter_jobs_list = get_letter_jobs()

    msg = ''
    if request.method == 'POST':
        send_letters = request.form.getlist('send_letter')
        for job_id in send_letters:
            job = [j for j in letter_jobs_list if job_id == j['job_id']][0]
            job['send'] = True

        msg = 'sending:{}'.format(send_letters)

    return render_template('views/letter-jobs.html', letter_jobs_list=letter_jobs_list, message=msg)


def get_letter_jobs():
    return [
        {
            'service_name': 'test_name',
            'job_id': 'test_id',
            'status': 'test_status',
            'created_at': '2017-04-01'
        },
        {
            'service_name': 'test_name 2',
            'job_id': 'test_id 2',
            'status': 'test_status 2',
            'created_at': '2017-04-02'

        },
        {
            'service_name': 'test_name 3',
            'job_id': 'test_id 3',
            'status': 'test_status 3',
            'created_at': '2017-04-03'
        }
    ]

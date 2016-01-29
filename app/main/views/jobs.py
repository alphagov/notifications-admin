# -*- coding: utf-8 -*-

import time

from flask import (
    render_template,
    abort
)
from flask_login import login_required
from client.errors import HTTPError

from app import job_api_client
from app.main import main

now = time.strftime('%H:%M')


@main.route("/services/<int:service_id>/jobs")
@login_required
def view_jobs(service_id):
    try:
        jobs = job_api_client.get_job(service_id)['data']
        return render_template(
            'views/jobs.html',
            jobs=jobs,
            service_id=service_id
        )
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e


@main.route("/services/<int:service_id>/jobs/<job_id>")
@login_required
def view_job(service_id, job_id):
    try:
        job = job_api_client.get_job(service_id, job_id)['data']
        messages = []
        return render_template(
            'views/job.html',
            messages=messages,
            counts={
                'total': len(messages),
                'delivered': len([
                    message for message in messages if message['status'] == 'Delivered'
                ]),
                'failed': len([
                    message for message in messages if message['status'] == 'Failed'
                ])
            },
            cost=u'£0.00',
            uploaded_file_name=job['original_file_name'],
            uploaded_file_time=job['created_at'],
            template_used=job['template'],
            flash_message="We’ve accepted {} for processing".format(job['original_file_name']),
            service_id=service_id
        )
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e


@main.route("/services/<int:service_id>/jobs/<job_id>/notification/<string:notification_id>")
@login_required
def view_notification(service_id, job_id, notification_id):
    return render_template(
        'views/notification.html',
        message=[
            message for message in messages if message['id'] == notification_id
        ][0],
        delivered_at=now,
        uploaded_at=now,
        service_id=service_id,
        job_id=job_id
    )

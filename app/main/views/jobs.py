# -*- coding: utf-8 -*-

import time

from flask import (
    render_template,
    abort
)
from flask_login import login_required
from notifications_python_client.errors import HTTPError
from notification_utils.template import Template

from app import job_api_client
from app.main import main
from app.main.dao import templates_dao
from app.main.dao import services_dao

now = time.strftime('%H:%M')


@main.route("/services/<service_id>/jobs")
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


@main.route("/services/<service_id>/jobs/<job_id>")
@login_required
def view_job(service_id, job_id):
    service = services_dao.get_service_by_id_or_404(service_id)
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
            template=Template(
                templates_dao.get_service_template_or_404(service_id, job['template'])['data'],
                prefix=service['name']
            ),
            service_id=service_id,
            service=service
        )
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e


@main.route("/services/<service_id>/jobs/<job_id>/notification/<string:notification_id>")
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

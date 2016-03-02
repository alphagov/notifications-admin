# -*- coding: utf-8 -*-

import time

from flask import (
    render_template,
    abort
)
from flask_login import login_required
from notifications_python_client.errors import HTTPError
from utils.template import Template

from app import job_api_client, notification_api_client
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
        notifications = notification_api_client.get_notifications_for_service(service_id, job_id)
        finished = job['status'] == 'finished'
        return render_template(
            'views/job.html',
            notifications=notifications['notifications'],
            counts={
                'queued': 0 if finished else job['notification_count'],
                'sent': job['notification_count'] if finished else 0,
                'failed': 0
            },
            uploaded_at=job['created_at'],
            finished_at=job['updated_at'] if finished else None,
            cost=u'£0.00',
            uploaded_file_name=job['original_file_name'],
            template=Template(
                templates_dao.get_service_template_or_404(service_id, job['template'])['data'],
                prefix=service['name']
            ),
            service_id=service_id,
            from_name=service['name'],
            job_id=job_id
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

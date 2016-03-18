# -*- coding: utf-8 -*-

import time

from flask import (
    render_template,
    abort,
    jsonify,
    flash,
    redirect,
    request,
    url_for
)
from flask_login import login_required
from utils.template import Template

from app import job_api_client, notification_api_client
from app.main import main
from app.main.dao import templates_dao
from app.main.dao import services_dao
from app.utils import (get_page_from_request, generate_previous_next_dict)


@main.route("/services/<service_id>/jobs")
@login_required
def view_jobs(service_id):
    jobs = job_api_client.get_job(service_id)['data']
    return render_template(
        'views/jobs/jobs.html',
        jobs=jobs,
        service_id=service_id
    )


@main.route("/services/<service_id>/jobs/<job_id>")
@login_required
def view_job(service_id, job_id):
    service = services_dao.get_service_by_id_or_404(service_id)
    job = job_api_client.get_job(service_id, job_id)['data']
    template = templates_dao.get_service_template_or_404(service_id, job['template'])['data']
    notifications = notification_api_client.get_notifications_for_service(service_id, job_id)
    finished = job['status'] == 'finished'
    return render_template(
        'views/jobs/job.html',
        notifications=notifications['notifications'],
        counts={
            'queued': 0 if finished else job['notification_count'],
            'sent': job['notification_count'] if finished else 0,
            'failed': 0,
            'cost': u'£0.00'
        },
        uploaded_at=job['created_at'],
        finished_at=job['updated_at'] if finished else None,
        uploaded_file_name=job['original_file_name'],
        template=Template(
            template,
            prefix=service['name'] if template['template_type'] == 'sms' else ''
        ),
        service_id=service_id,
        service=service,
        job_id=job_id
    )


@main.route("/services/<service_id>/jobs/<job_id>.json")
@login_required
def view_job_updates(service_id, job_id):
    service = services_dao.get_service_by_id_or_404(service_id)
    job = job_api_client.get_job(service_id, job_id)['data']
    notifications = notification_api_client.get_notifications_for_service(service_id, job_id)
    finished = job['status'] == 'finished'
    return jsonify(**{
        'counts': render_template(
            'partials/jobs/count.html',
            counts={
                'queued': 0 if finished else job['notification_count'],
                'sent': job['notification_count'] if finished else 0,
                'failed': 0,
                'cost': u'£0.00'
            }
        ),
        'notifications': render_template(
            'partials/jobs/notifications.html',
            notifications=notifications['notifications']
        ),
        'status': render_template(
            'partials/jobs/status.html',
            uploaded_at=job['created_at'],
            finished_at=job['updated_at'] if finished else None
        ),
    })


@main.route('/services/<service_id>/notifications')
@login_required
def view_notifications(service_id):
    # TODO get the api to return count of pages as well.
    page = get_page_from_request()
    if page is None:
        abort(404, "Invalid page argument ({}) reverting to page 1.".format(request.args['page'], None))
    notifications = notification_api_client.get_notifications_for_service(service_id=service_id, page=page)
    prev_page = None
    if notifications['links'].get('prev', None):
        prev_page = generate_previous_next_dict(
            'main.view_notifications',
            {'service_id': service_id}, page - 1, 'Previous page', 'page {}'.format(page - 1))
    next_page = None
    if notifications['links'].get('next', None):
        next_page = generate_previous_next_dict(
            'main.view_notifications',
            {'service_id': service_id}, page + 1, 'Next page', 'page {}'.format(page + 1))
    return render_template(
        'views/notifications.html',
        service_id=service_id,
        notifications=notifications['notifications'],
        page=page,
        prev_page=prev_page,
        next_page=next_page
    )


@main.route("/services/<service_id>/jobs/<job_id>/notification/<string:notification_id>")
@login_required
def view_notification(service_id, job_id, notification_id):

    now = time.strftime('%H:%M')

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

# -*- coding: utf-8 -*-

import time

from flask import (
    render_template,
    abort,
    jsonify,
    request,
    url_for,
    current_app
)
from flask_login import login_required
from werkzeug.datastructures import MultiDict
from notifications_utils.template import Template

from app import (
    job_api_client,
    notification_api_client,
    service_api_client,
    current_service)
from app.main import main
from app.utils import (
    get_page_from_request,
    generate_previous_next_dict,
    user_has_permissions,
    generate_notifications_csv)


def _parse_filter_args(filter_dict):
    if not isinstance(filter_dict, MultiDict):
        filter_dict = MultiDict(filter_dict)

    return MultiDict(
        (
            key,
            (','.join(filter_dict.getlist(key))).split(',')
        )
        for key in filter_dict.keys()
        if ''.join(filter_dict.getlist(key))
    )


@main.route("/services/<service_id>/jobs")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_jobs(service_id):
    jobs = job_api_client.get_job(service_id)['data']
    return render_template(
        'views/jobs/jobs.html',
        jobs=jobs
    )


@main.route("/services/<service_id>/jobs/<job_id>")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_job(service_id, job_id):
    job = job_api_client.get_job(service_id, job_id)['data']
    template = service_api_client.get_service_template(service_id, job['template'])['data']
    notifications = notification_api_client.get_notifications_for_service(service_id, job_id)
    finished = job['status'] == 'finished'
    return render_template(
        'views/jobs/job.html',
        notifications=notifications['notifications'],
        counts={
            'queued': 0 if finished else job['notification_count'],
            'sent': job['notification_count'] if finished else 0
        },
        uploaded_at=job['created_at'],
        finished_at=job['updated_at'] if finished else None,
        uploaded_file_name=job['original_file_name'],
        template=Template(
            template,
            prefix=current_service['name']
        ),
        job_id=job_id
    )


@main.route("/services/<service_id>/jobs/<job_id>.json")
@login_required
@user_has_permissions('view_activity')
def view_job_updates(service_id, job_id):
    job = job_api_client.get_job(service_id, job_id)['data']
    notifications = notification_api_client.get_notifications_for_service(service_id, job_id)
    finished = job['status'] == 'finished'
    return jsonify(**{
        'counts': render_template(
            'partials/jobs/count.html',
            counts={
                'queued': 0 if finished else job['notification_count'],
                'sent': job['notification_count'] if finished else 0
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
@user_has_permissions('view_activity', admin_override=True)
def view_notifications(service_id):
    # TODO get the api to return count of pages as well.
    page = get_page_from_request()
    if page is None:
        abort(404, "Invalid page argument ({}) reverting to page 1.".format(request.args['page'], None))

    filter_args = _parse_filter_args(request.args)

    notifications = notification_api_client.get_notifications_for_service(
        service_id=service_id,
        page=page,
        template_type=filter_args.get('template_type') if 'template_type' in filter_args else ['email', 'sms'],
        status=filter_args.get('status') if 'status' in filter_args else ['delivered', 'failed'],
        limit_days=current_app.config['ACTIVITY_STATS_LIMIT_DAYS'])
    view_dict = MultiDict(request.args)
    prev_page = None
    if notifications['links'].get('prev', None):
        prev_page = generate_previous_next_dict(
            'main.view_notifications',
            service_id,
            view_dict,
            page - 1,
            'Previous page',
            'page {}'.format(page - 1))
    next_page = None
    if notifications['links'].get('next', None):
        next_page = generate_previous_next_dict(
            'main.view_notifications',
            service_id,
            view_dict,
            page + 1,
            'Next page',
            'page {}'.format(page + 1))
    if 'download' in request.args and request.args['download'] == 'csv':
        csv_content = generate_notifications_csv(
            notification_api_client.get_notifications_for_service(
                service_id=service_id,
                page=page,
                page_size=notifications['total'],
                template_type=filter_args.getlist('template_type') if 'template_type' in filter_args else None,
                status=filter_args.getlist('status')
                if 'status' in filter_args else ['delivered', 'failed'],
                limit_days=current_app.config['ACTIVITY_STATS_LIMIT_DAYS'])['notifications'])
        return csv_content, 200, {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': 'inline; filename="notifications.csv"'
        }
    return render_template(
        'views/notifications.html',
        notifications=notifications['notifications'],
        page=page,
        prev_page=prev_page,
        next_page=next_page,
        request_args=request.args,
        type_filters=[
            [item[0], item[1], url_for(
                '.view_notifications',
                service_id=current_service['id'],
                template_type=item[1],
                status=request.args.get('status', 'delivered,failed')
            )] for item in [
                ['Emails', 'email'],
                ['Text messages', 'sms'],
                ['Both', 'email,sms']
            ]
        ],
        status_filters=[
            [item[0], item[1], url_for(
                '.view_notifications',
                service_id=current_service['id'],
                template_type=request.args.get('template_type', 'email,sms'),
                status=item[1]
            )] for item in [
                ['Successful', 'delivered'],
                ['Failed', 'failed'],
                ['Both', 'delivered,failed']
            ]
        ]
    )


@main.route("/services/<service_id>/jobs/<job_id>/notification/<string:notification_id>")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_notification(service_id, job_id, notification_id):

    now = time.strftime('%H:%M')

    return render_template(
        'views/notification.html',
        message=[
            message for message in messages if message['id'] == notification_id
        ][0],
        delivered_at=now,
        uploaded_at=now,
        job_id=job_id
    )

# -*- coding: utf-8 -*-
import ago
import time
import dateutil
from orderedset import OrderedSet
from datetime import datetime, timedelta, timezone
from itertools import chain

from flask import (
    render_template,
    abort,
    jsonify,
    request,
    url_for,
    current_app,
    redirect
)
from flask_login import login_required
from werkzeug.datastructures import MultiDict
from notifications_utils.template import Template

from app import (
    job_api_client,
    notification_api_client,
    service_api_client,
    current_service,
    format_datetime_short)
from app.main import main
from app.utils import (
    get_page_from_request,
    generate_previous_next_dict,
    user_has_permissions,
    generate_notifications_csv)
from app.statistics_utils import add_rate_to_jobs
from app.utils import get_help_argument


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


def _set_status_filters(filter_args):
    status_filters = filter_args.get('status', [])
    all_failure_statuses = ['failed', 'temporary-failure', 'permanent-failure', 'technical-failure']
    all_sending_statuses = ['created', 'sending']
    return list(OrderedSet(chain(
        (status_filters or all_sending_statuses + ['delivered'] + all_failure_statuses),
        all_sending_statuses if 'sending' in status_filters else [],
        all_failure_statuses if 'failed' in status_filters else []
    )))


@main.route("/services/<service_id>/jobs")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_jobs(service_id):
    return render_template(
        'views/jobs/jobs.html',
        jobs=add_rate_to_jobs([
            job for job in job_api_client.get_job(service_id)['data']
            if job['job_status'] not in ['scheduled', 'cancelled']
        ])
    )


@main.route("/services/<service_id>/jobs/<job_id>")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_job(service_id, job_id):
    job = job_api_client.get_job(service_id, job_id)['data']

    if job['job_status'] == 'cancelled':
        abort(404)

    filter_args = _parse_filter_args(request.args)
    filter_args['status'] = _set_status_filters(filter_args)

    total_notifications = job.get('notification_count', 0)
    processed_notifications = job.get('notifications_delivered', 0) + job.get('notifications_failed', 0)

    return render_template(
        'views/jobs/job.html',
        finished=(total_notifications == processed_notifications),
        uploaded_file_name=job['original_file_name'],
        template=Template(
            service_api_client.get_service_template(
                service_id=service_id,
                template_id=job['template'],
                version=job['template_version']
            )['data'],
            prefix=current_service['name'],
            sms_sender=current_service['sms_sender']
        ),
        status=request.args.get('status', ''),
        updates_url=url_for(
            ".view_job_updates",
            service_id=service_id,
            job_id=job['id'],
            status=request.args.get('status', ''),
            help=get_help_argument()
        ),
        partials=get_job_partials(job),
        help=get_help_argument()
    )


@main.route("/services/<service_id>/jobs/<job_id>.csv")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_job_csv(service_id, job_id):
    job = job_api_client.get_job(service_id, job_id)['data']
    template = service_api_client.get_service_template(
        service_id=service_id,
        template_id=job['template'],
        version=job['template_version']
    )['data']
    filter_args = _parse_filter_args(request.args)
    filter_args['status'] = _set_status_filters(filter_args)

    return (
        generate_notifications_csv(
            notification_api_client.get_notifications_for_service(
                service_id,
                job_id,
                status=filter_args.get('status'),
                page_size=job['notification_count']
            )['notifications']
        ),
        200,
        {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': 'inline; filename="{} - {}.csv"'.format(
                template['name'],
                format_datetime_short(job['created_at'])
            )
        }
    )


@main.route("/services/<service_id>/jobs/<job_id>", methods=['POST'])
@login_required
@user_has_permissions('send_texts', 'send_emails', 'send_letters', admin_override=True)
def cancel_job(service_id, job_id):
    job_api_client.cancel_job(service_id, job_id)
    return redirect(url_for('main.service_dashboard', service_id=service_id))


@main.route("/services/<service_id>/jobs/<job_id>.json")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_job_updates(service_id, job_id):
    return jsonify(**get_job_partials(
        job_api_client.get_job(service_id, job_id)['data']
    ))


@main.route('/services/<service_id>/notifications/<message_type>')
@main.route('/services/<service_id>/notifications/<message_type>.csv', endpoint="view_notifications_csv")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_notifications(service_id, message_type):
    # TODO get the api to return count of pages as well.
    page = get_page_from_request()
    if page is None:
        abort(404, "Invalid page argument ({}) reverting to page 1.".format(request.args['page'], None))
    if message_type not in ['email', 'sms']:
        abort(404)

    filter_args = _parse_filter_args(request.args)
    filter_args['status'] = _set_status_filters(filter_args)

    notifications = notification_api_client.get_notifications_for_service(
        service_id=service_id,
        page=page,
        template_type=[message_type],
        status=filter_args.get('status'),
        limit_days=current_app.config['ACTIVITY_STATS_LIMIT_DAYS'])
    view_dict = dict(
        message_type=message_type,
        status=request.args.get('status')
    )
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
    if request.path.endswith('csv'):
        csv_content = generate_notifications_csv(
            notification_api_client.get_notifications_for_service(
                service_id=service_id,
                page=page,
                page_size=notifications['total'],
                template_type=[message_type],
                status=filter_args.get('status'),
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
        status=request.args.get('status'),
        message_type=message_type,
        download_link=url_for(
            '.view_notifications_csv',
            service_id=current_service['id'],
            message_type=message_type,
            status=request.args.get('status')
        ),
        status_filters=get_status_filters(
            current_service,
            message_type,
            service_api_client.get_detailed_service(service_id)['data']['statistics']
        )
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


def get_status_filters(service, message_type, statistics):
    stats = statistics[message_type]
    stats['sending'] = stats['requested'] - stats['delivered'] - stats['failed']

    filters = [
        # key, label, option
        ('requested', 'total', 'sending,delivered,failed'),
        ('sending', 'sending', 'sending'),
        ('delivered', 'delivered', 'delivered'),
        ('failed', 'failed', 'failed'),
    ]
    return [
        # return list containing label, option, link, count
        (
            label,
            option,
            url_for(
                '.view_notifications',
                service_id=service['id'],
                message_type=message_type,
                status=option
            ),
            stats[key]
        )
        for key, label, option in filters
        ]


def _get_job_counts(job, help_argument):
    sending = 0 if job['job_status'] == 'scheduled' else (
        job.get('notification_count', 0) -
        job.get('notifications_delivered', 0) -
        job.get('notifications_failed', 0)
    )
    return [
        (
            label,
            query_param,
            url_for(
                ".view_job",
                service_id=job['service'],
                job_id=job['id'],
                status=query_param,
                help=help_argument
            ),
            count
        ) for label, query_param, count in [
            [
              'total', '',
              job.get('notification_count', 0)
            ],
            [
              'sending', 'sending',
              sending
            ],
            [
              'delivered', 'delivered',
              job.get('notifications_delivered', 0)
            ],
            [
              'failed', 'failed',
              job.get('notifications_failed', 0)
            ]
        ]
    ]


def get_job_partials(job):
    filter_args = _parse_filter_args(request.args)
    filter_args['status'] = _set_status_filters(filter_args)
    notifications = notification_api_client.get_notifications_for_service(
        job['service'], job['id'], status=filter_args['status']
    )
    return {
        'counts': render_template(
            'partials/jobs/count.html',
            counts=_get_job_counts(job, request.args.get('help', 0)),
            status=filter_args['status']
        ),
        'notifications': render_template(
            'partials/jobs/notifications.html',
            notifications=notifications['notifications'],
            more_than_one_page=bool(notifications.get('links', {}).get('next')),
            percentage_complete=(job['notifications_requested'] / job['notification_count'] * 100),
            download_link=url_for(
                '.view_job_csv',
                service_id=current_service['id'],
                job_id=job['id'],
                status=request.args.get('status')
            ),
            help=get_help_argument(),
            time_left=get_time_left(job['created_at']),
            job=job
        ),
        'status': render_template(
            'partials/jobs/status.html',
            job=job
        ),
    }


def get_time_left(job_created_at):
    return ago.human(
        (
            datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
        ) - (
            dateutil.parser.parse(job_created_at) + timedelta(days=8)
        ),
        future_tense='Data available for {}',
        past_tense='Data no longer available',  # No-one should ever see this
        precision=1
    )

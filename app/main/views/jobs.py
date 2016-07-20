# -*- coding: utf-8 -*-

import time
import dateutil
from datetime import datetime, timedelta, timezone
import ago

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
    statistics_api_client,
    current_service,
    format_datetime_short)
from app.main import main
from app.utils import (
    get_page_from_request,
    generate_previous_next_dict,
    user_has_permissions,
    generate_notifications_csv)
from app.statistics_utils import sum_of_statistics, statistics_by_state, add_rate_to_jobs
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
    all_failure_statuses = ['failed', 'temporary-failure', 'permanent-failure', 'technical-failure']
    all_statuses = ['sending', 'delivered'] + all_failure_statuses
    if filter_args.get('status'):
        if 'processed' in filter_args.get('status') or not filter_args.get('status'):
            filter_args['status'] = all_statuses
        elif 'failed' in filter_args.get('status'):
            filter_args['status'].extend(all_failure_statuses[1:])
    else:
        filter_args['status'] = all_statuses


@main.route("/services/<service_id>/jobs")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_jobs(service_id):
    return render_template(
        'views/jobs/jobs.html',
        jobs=add_rate_to_jobs(job_api_client.get_job(service_id)['data'])
    )


@main.route("/services/<service_id>/jobs/<job_id>")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_job(service_id, job_id):

    job = job_api_client.get_job(service_id, job_id)['data']
    filter_args = _parse_filter_args(request.args)
    _set_status_filters(filter_args)

    return render_template(
        'views/jobs/job.html',
        finished=job.get('notifications_sent', 0) and ((
            job.get('notifications_sent', 0) -
            job.get('notifications_delivered', 0) -
            job.get('notifications_failed', 0)
        ) == 0),
        uploaded_file_name=job['original_file_name'],
        template=Template(
            service_api_client.get_service_template(
                service_id=service_id,
                template_id=job['template'],
                version=job['template_version']
            )['data'],
            prefix=current_service['name']
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
    _set_status_filters(filter_args)

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
    _set_status_filters(filter_args)

    notifications = notification_api_client.get_notifications_for_service(
        service_id=service_id,
        page=page,
        template_type=[message_type],
        status=filter_args.get('status'),
        limit_days=current_app.config['ACTIVITY_STATS_LIMIT_DAYS'])
    service_statistics_by_state = statistics_by_state(sum_of_statistics(
        statistics_api_client.get_statistics_for_service(service_id, limit_days=7)['data']
    ))
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
        request_args=request.args,
        message_type=message_type,
        download_link=url_for(
            '.view_notifications_csv',
            service_id=current_service['id'],
            message_type=message_type,
            status=request.args.get('status')
        ),
        status_filters=[
            [
                item[0], item[1],
                url_for(
                    '.view_notifications',
                    service_id=current_service['id'],
                    message_type=message_type,
                    status=item[1]
                ),
                service_statistics_by_state[message_type][item[0]]
            ] for item in [
                ['processed', 'sending,delivered,failed'],
                ['sending', 'sending'],
                ['delivered', 'delivered'],
                ['failed', 'failed'],
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


def _get_job_counts(job, help_argument):
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
              'Processed', '',
              job.get('notifications_sent', 0)
            ],
            [
              'Sending', 'sending',
              (
                  job.get('notifications_sent', 0) -
                  job.get('notifications_delivered', 0) -
                  job.get('notifications_failed', 0)
              )
            ],
            [
              'Delivered', 'delivered',
              job.get('notifications_delivered', 0)
            ],
            [
              'Failed', 'failed',
              job.get('notifications_failed')
            ]
        ]
    ]


def get_job_partials(job):
    filter_args = _parse_filter_args(request.args)
    _set_status_filters(filter_args)
    return {
        'counts': render_template(
            'partials/jobs/count.html',
            job=job,
            counts=_get_job_counts(job, request.args.get('help', 0)),
            status=request.args.get('status', '')
        ),
        'notifications': render_template(
            'partials/jobs/notifications.html',
            notifications=notification_api_client.get_notifications_for_service(
                job['service'], job['id'], status=filter_args.get('status')
            )['notifications'],
            download_link=url_for(
                '.view_job_csv',
                service_id=current_service['id'],
                job_id=job['id'],
                status=request.args.get('status', '')
            ),
            help=get_help_argument(),
            time_left=get_time_left(job['created_at'])
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

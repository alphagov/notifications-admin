# -*- coding: utf-8 -*-
import ago
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
    redirect,
    Response,
    stream_with_context
)
from flask_login import login_required
from werkzeug.datastructures import MultiDict

from app import (
    job_api_client,
    notification_api_client,
    service_api_client,
    current_service,
    format_datetime_short)
from app.main import main
from app.utils import (
    get_page_from_request,
    generate_next_dict,
    generate_previous_dict,
    user_has_permissions,
    generate_notifications_csv,
    get_help_argument,
    get_template,
    REQUESTED_STATUSES,
    FAILURE_STATUSES,
    SENDING_STATUSES,
    DELIVERED_STATUSES,
)
from app.statistics_utils import add_rate_to_job


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
    return list(OrderedSet(chain(
        (status_filters or REQUESTED_STATUSES),
        DELIVERED_STATUSES if 'delivered' in status_filters else [],
        SENDING_STATUSES if 'sending' in status_filters else [],
        FAILURE_STATUSES if 'failed' in status_filters else []
    )))


@main.route("/services/<service_id>/jobs")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_jobs(service_id):
    page = int(request.args.get('page', 1))
    # all but scheduled and cancelled
    statuses_to_display = job_api_client.JOB_STATUSES - {'scheduled', 'cancelled'}
    jobs_response = job_api_client.get_jobs(service_id, statuses=statuses_to_display, page=page)
    jobs = [
        add_rate_to_job(job) for job in jobs_response['data']
    ]

    prev_page = None
    if jobs_response['links'].get('prev', None):
        prev_page = generate_previous_dict('main.view_jobs', service_id, page)
    next_page = None
    if jobs_response['links'].get('next', None):
        next_page = generate_next_dict('main.view_jobs', service_id, page)

    return render_template(
        'views/jobs/jobs.html',
        jobs=jobs,
        page=page,
        prev_page=prev_page,
        next_page=next_page,
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
        template=get_template(
            service_api_client.get_service_template(
                service_id=service_id,
                template_id=job['template'],
                version=job['template_version']
            )['data'],
            current_service,
            letter_preview_url=url_for(
                '.view_template_version_preview',
                service_id=service_id,
                template_id=job['template'],
                version=job['template_version'],
                filetype='png',
            ),
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

    return Response(
        stream_with_context(
            generate_notifications_csv(
                service_id=service_id,
                job_id=job_id,
                status=filter_args.get('status'),
                page=request.args.get('page', 1),
                page_size=5000,
                format_for_csv=True
            )
        ),
        mimetype='text/csv',
        headers={
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
@user_has_permissions('view_activity', admin_override=True)
def view_job_updates(service_id, job_id):
    return jsonify(**get_job_partials(
        job_api_client.get_job(service_id, job_id)['data']
    ))


@main.route('/services/<service_id>/notifications/<message_type>')
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_notifications(service_id, message_type):
    return render_template(
        'views/notifications.html',
        partials=get_notifications(service_id, message_type),
        message_type=message_type,
        status=request.args.get('status'),
        page=request.args.get('page', 1),
        to=request.args.get('to'),
    )


@main.route('/services/<service_id>/notifications/<message_type>.json')
@user_has_permissions('view_activity', admin_override=True)
def get_notifications_as_json(service_id, message_type):
    return jsonify(get_notifications(
        service_id, message_type, status_override=request.args.get('status')
    ))


@main.route('/services/<service_id>/notifications/<message_type>.csv', endpoint="view_notifications_csv")
@user_has_permissions('view_activity', admin_override=True)
def get_notifications(service_id, message_type, status_override=None):
    # TODO get the api to return count of pages as well.
    page = get_page_from_request()
    if page is None:
        abort(404, "Invalid page argument ({}) reverting to page 1.".format(request.args['page'], None))
    if message_type not in ['email', 'sms']:
        abort(404)
    filter_args = _parse_filter_args(request.args)
    filter_args['status'] = _set_status_filters(filter_args)
    if request.path.endswith('csv'):
        return Response(
            generate_notifications_csv(
                service_id=service_id,
                page=page,
                page_size=5000,
                template_type=[message_type],
                status=filter_args.get('status'),
                limit_days=current_app.config['ACTIVITY_STATS_LIMIT_DAYS']
            ),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'inline; filename="notifications.csv"'}
        )

    notifications = notification_api_client.get_notifications_for_service(
        service_id=service_id,
        page=page,
        template_type=[message_type],
        status=filter_args.get('status'),
        limit_days=current_app.config['ACTIVITY_STATS_LIMIT_DAYS'],
        to=request.args.get('to'),
    )

    url_args = {
        'message_type': message_type,
        'status': request.args.get('status')
    }
    prev_page = None

    if notifications['links'].get('prev', None):
        prev_page = generate_previous_dict('main.view_notifications', service_id, page, url_args=url_args)
    next_page = None

    if notifications['links'].get('next', None):
        next_page = generate_next_dict('main.view_notifications', service_id, page, url_args)

    return {
        'counts': render_template(
            'views/activity/counts.html',
            status=request.args.get('status'),
            status_filters=get_status_filters(
                current_service,
                message_type,
                service_api_client.get_detailed_service(service_id)['data']['statistics']
            )
        ),
        'notifications': render_template(
            'views/activity/notifications.html',
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
            )
        ),
    }


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

# -*- coding: utf-8 -*-

from datetime import datetime

from flask import (
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    stream_with_context,
    url_for,
)
from flask_login import current_user
from notifications_python_client.errors import HTTPError
from notifications_utils.letter_timings import (
    CANCELLABLE_JOB_LETTER_STATUSES,
    get_letter_timings,
    letter_can_be_cancelled,
)
from notifications_utils.template import Template, WithSubjectTemplate

from app import (
    current_service,
    format_datetime_short,
    format_thousands,
    job_api_client,
    notification_api_client,
    service_api_client,
)
from app.main import main
from app.main.forms import SearchNotificationsForm
from app.statistics_utils import add_rate_to_job
from app.utils import (
    generate_next_dict,
    generate_notifications_csv,
    generate_previous_dict,
    get_letter_printing_statement,
    get_page_from_request,
    get_time_left,
    parse_filter_args,
    printing_today_or_tomorrow,
    set_status_filters,
    user_has_permissions,
)


@main.route("/services/<uuid:service_id>/jobs")
@user_has_permissions()
def view_jobs(service_id):
    page = int(request.args.get('page', 1))
    jobs_response = job_api_client.get_page_of_jobs(service_id, page=page)
    jobs = [
        add_rate_to_job(job) for job in jobs_response['data']
    ]

    prev_page = None
    if jobs_response['links'].get('prev', None):
        prev_page = generate_previous_dict('main.view_jobs', service_id, page)
    next_page = None
    if jobs_response['links'].get('next', None):
        next_page = generate_next_dict('main.view_jobs', service_id, page)

    scheduled_jobs = ''
    if not current_user.has_permissions('view_activity') and page == 1:
        scheduled_jobs = render_template(
            'views/dashboard/_upcoming.html',
            scheduled_jobs=job_api_client.get_scheduled_jobs(service_id),
            hide_heading=True,
        )

    return render_template(
        'views/jobs/jobs.html',
        jobs=jobs,
        page=page,
        prev_page=prev_page,
        next_page=next_page,
        scheduled_jobs=scheduled_jobs,
    )


@main.route("/services/<uuid:service_id>/jobs/<uuid:job_id>")
@user_has_permissions()
def view_job(service_id, job_id):
    job = job_api_client.get_job(service_id, job_id)['data']
    if job['job_status'] == 'cancelled':
        abort(404)

    filter_args = parse_filter_args(request.args)
    filter_args['status'] = set_status_filters(filter_args)

    total_notifications = job.get('notification_count', 0)
    processed_notifications = job.get('notifications_delivered', 0) + job.get('notifications_failed', 0)

    template = service_api_client.get_service_template(
        service_id=service_id,
        template_id=job['template'],
        version=job['template_version']
    )['data']

    just_sent_message = 'Your {} been sent. Printing starts {} at 5:30pm.'.format(
        'letter has' if job['notification_count'] == 1 else 'letters have',
        printing_today_or_tomorrow()
    )
    partials = get_job_partials(job, template)
    can_cancel_letter_job = partials["can_letter_job_be_cancelled"]

    return render_template(
        'views/jobs/job.html',
        finished=(total_notifications == processed_notifications),
        uploaded_file_name=job['original_file_name'],
        template_id=job['template'],
        job_id=job_id,
        status=request.args.get('status', ''),
        updates_url=url_for(
            ".view_job_updates",
            service_id=service_id,
            job_id=job['id'],
            status=request.args.get('status', ''),
        ),
        partials=partials,
        just_sent=bool(
            request.args.get('just_sent') == 'yes'
            and template['template_type'] == 'letter'
        ),
        just_sent_message=just_sent_message,
        can_cancel_letter_job=can_cancel_letter_job,
    )


@main.route("/services/<uuid:service_id>/jobs/<uuid:job_id>.csv")
@user_has_permissions('view_activity')
def view_job_csv(service_id, job_id):
    job = job_api_client.get_job(service_id, job_id)['data']
    template = service_api_client.get_service_template(
        service_id=service_id,
        template_id=job['template'],
        version=job['template_version']
    )['data']
    filter_args = parse_filter_args(request.args)
    filter_args['status'] = set_status_filters(filter_args)

    return Response(
        stream_with_context(
            generate_notifications_csv(
                service_id=service_id,
                job_id=job_id,
                status=filter_args.get('status'),
                page=request.args.get('page', 1),
                page_size=5000,
                format_for_csv=True,
                template_type=template['template_type'],
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


@main.route("/services/<uuid:service_id>/jobs/<uuid:job_id>", methods=['POST'])
@user_has_permissions('send_messages')
def cancel_job(service_id, job_id):
    job_api_client.cancel_job(service_id, job_id)
    return redirect(url_for('main.service_dashboard', service_id=service_id))


@main.route("/services/<uuid:service_id>/jobs/<uuid:job_id>/cancel", methods=['GET', 'POST'])
@user_has_permissions()
def cancel_letter_job(service_id, job_id):
    if request.method == 'POST':
        job = job_api_client.get_job(service_id, job_id)['data']
        notification_count = notification_api_client.get_notification_count_for_job_id(
            service_id=service_id, job_id=job_id
        )
        if job['job_status'] != 'finished' or notification_count < job['notification_count']:
            flash("We are still processing these letters, please try again in a minute.", 'try again')
            return view_job(service_id, job_id)
        try:
            number_of_letters = job_api_client.cancel_letter_job(current_service.id, job_id)
        except HTTPError as e:
            flash(e.message, 'dangerous')
            return redirect(url_for('main.view_job', service_id=service_id, job_id=job_id))
        flash("Cancelled {} letters from {}".format(
            format_thousands(number_of_letters), job['original_file_name']
        ), 'default_with_tick')
        return redirect(url_for('main.service_dashboard', service_id=service_id))

    flash("Are you sure you want to cancel sending these letters?", 'cancel')
    return view_job(service_id, job_id)


@main.route("/services/<uuid:service_id>/jobs/<uuid:job_id>.json")
@user_has_permissions()
def view_job_updates(service_id, job_id):

    job = job_api_client.get_job(service_id, job_id)['data']

    return jsonify(**get_job_partials(
        job,
        service_api_client.get_service_template(
            service_id=current_service.id,
            template_id=job['template'],
            version=job['template_version']
        )['data'],
    ))


@main.route('/services/<uuid:service_id>/notifications', methods=['GET', 'POST'])
@main.route('/services/<uuid:service_id>/notifications/<template_type:message_type>', methods=['GET', 'POST'])
@user_has_permissions()
def view_notifications(service_id, message_type=None):
    return render_template(
        'views/notifications.html',
        partials=get_notifications(service_id, message_type),
        message_type=message_type,
        status=request.args.get('status') or 'sending,delivered,failed',
        page=request.args.get('page', 1),
        to=request.form.get('to', ''),
        search_form=SearchNotificationsForm(
            message_type=message_type,
            to=request.form.get('to', ''),
        ),
        download_link=url_for(
            '.download_notifications_csv',
            service_id=current_service.id,
            message_type=message_type,
            status=request.args.get('status')
        )
    )


@main.route('/services/<uuid:service_id>/notifications.json', methods=['GET', 'POST'])
@main.route('/services/<uuid:service_id>/notifications/<template_type:message_type>.json', methods=['GET', 'POST'])
@user_has_permissions()
def get_notifications_as_json(service_id, message_type=None):
    return jsonify(get_notifications(
        service_id, message_type, status_override=request.args.get('status')
    ))


@main.route('/services/<uuid:service_id>/notifications.csv', endpoint="view_notifications_csv")
@main.route(
    '/services/<uuid:service_id>/notifications/<template_type:message_type>.csv',
    endpoint="view_notifications_csv"
)
@user_has_permissions()
def get_notifications(service_id, message_type, status_override=None):
    # TODO get the api to return count of pages as well.
    page = get_page_from_request()
    if page is None:
        abort(404, "Invalid page argument ({}).".format(request.args.get('page')))
    filter_args = parse_filter_args(request.args)
    filter_args['status'] = set_status_filters(filter_args)
    service_data_retention_days = None

    if message_type is not None:
        service_data_retention_days = current_service.get_days_of_retention(message_type)

    if request.path.endswith('csv') and current_user.has_permissions('view_activity'):
        return Response(
            generate_notifications_csv(
                service_id=service_id,
                page=page,
                page_size=5000,
                template_type=[message_type],
                status=filter_args.get('status'),
                limit_days=service_data_retention_days
            ),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'inline; filename="notifications.csv"'}
        )
    notifications = notification_api_client.get_notifications_for_service(
        service_id=service_id,
        page=page,
        template_type=[message_type] if message_type else [],
        status=filter_args.get('status'),
        limit_days=service_data_retention_days,
        to=request.form.get('to', ''),
    )
    url_args = {
        'message_type': message_type,
        'status': request.args.get('status')
    }
    prev_page = None

    if 'links' in notifications and notifications['links'].get('prev', None):
        prev_page = generate_previous_dict('main.view_notifications', service_id, page, url_args=url_args)
    next_page = None

    if 'links' in notifications and notifications['links'].get('next', None):
        next_page = generate_next_dict('main.view_notifications', service_id, page, url_args)

    if message_type:
        download_link = url_for(
            '.view_notifications_csv',
            service_id=current_service.id,
            message_type=message_type,
            status=request.args.get('status')
        )
    else:
        download_link = None

    return {
        'service_data_retention_days': service_data_retention_days,
        'counts': render_template(
            'views/activity/counts.html',
            status=request.args.get('status'),
            status_filters=get_status_filters(
                current_service,
                message_type,
                service_api_client.get_service_statistics(
                    service_id,
                    today_only=False,
                    limit_days=service_data_retention_days
                )
            )
        ),
        'notifications': render_template(
            'views/activity/notifications.html',
            notifications=list(add_preview_of_content_to_notifications(
                notifications['notifications']
            )),
            page=page,
            limit_days=service_data_retention_days,
            prev_page=prev_page,
            next_page=next_page,
            status=request.args.get('status'),
            message_type=message_type,
            download_link=download_link,
        ),
    }


def get_status_filters(service, message_type, statistics):
    if message_type is None:
        stats = {
            key: sum(
                statistics[message_type][key]
                for message_type in {'email', 'sms', 'letter'}
            )
            for key in {'requested', 'delivered', 'failed'}
        }
    else:
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
                service_id=service.id,
                message_type=message_type,
                status=option
            ),
            stats[key]
        )
        for key, label, option in filters
    ]


def _get_job_counts(job):
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


def get_job_partials(job, template):
    filter_args = parse_filter_args(request.args)
    filter_args['status'] = set_status_filters(filter_args)
    notifications = notification_api_client.get_notifications_for_service(
        job['service'], job['id'], status=filter_args['status']
    )

    if template['template_type'] == 'letter':
        # there might be no notifications if the job has only just been created and the tasks haven't run yet
        if notifications['notifications']:
            postage = notifications['notifications'][0]['postage']
        else:
            postage = template['postage']

        counts = render_template(
            'partials/jobs/count-letters.html',
            total=job.get('notification_count', 0),
            delivery_estimate=get_letter_timings(job['created_at'], postage=postage).earliest_delivery,
        )
    else:
        counts = render_template(
            'partials/count.html',
            counts=_get_job_counts(job),
            status=filter_args['status']
        )
    service_data_retention_days = current_service.get_days_of_retention(template['template_type'])
    can_letter_job_be_cancelled = False
    if template["template_type"] == "letter":
        not_cancellable = [
            n for n in notifications["notifications"] if n["status"] not in CANCELLABLE_JOB_LETTER_STATUSES
        ]
        job_created = job["created_at"][:-6]
        if not letter_can_be_cancelled(
            "created", datetime.strptime(job_created, '%Y-%m-%dT%H:%M:%S.%f')
        ) or len(not_cancellable) != 0:
            can_letter_job_be_cancelled = False
        else:
            can_letter_job_be_cancelled = True
    return {
        'counts': counts,
        'notifications': render_template(
            'partials/jobs/notifications.html',
            notifications=list(
                add_preview_of_content_to_notifications(notifications['notifications'])
            ),
            more_than_one_page=bool(notifications.get('links', {}).get('next')),
            percentage_complete=(job['notifications_requested'] / job['notification_count'] * 100),
            download_link=url_for(
                '.view_job_csv',
                service_id=current_service.id,
                job_id=job['id'],
                status=request.args.get('status')
            ),
            time_left=get_time_left(job['created_at'], service_data_retention_days=service_data_retention_days),
            job=job,
            template=template,
            template_version=job['template_version'],
        ),
        'status': render_template(
            'partials/jobs/status.html',
            job=job,
            template_type=template["template_type"],
            letter_print_day=get_letter_printing_statement("created", job["created_at"])
        ),
        'can_letter_job_be_cancelled': can_letter_job_be_cancelled,
    }


def add_preview_of_content_to_notifications(notifications):

    for notification in notifications:

        if notification['template'].get('redact_personalisation'):
            notification['personalisation'] = {}

        if notification['template']['template_type'] == 'sms':
            yield dict(
                preview_of_content=str(Template(
                    notification['template'],
                    notification['personalisation'],
                    redact_missing_personalisation=True,
                )),
                **notification
            )
        else:
            if notification['template']['is_precompiled_letter']:
                notification['template']['subject'] = 'Provided as PDF'
            yield dict(
                preview_of_content=(
                    WithSubjectTemplate(
                        notification['template'],
                        notification['personalisation'],
                        redact_missing_personalisation=True,
                    ).subject
                ),
                **notification
            )

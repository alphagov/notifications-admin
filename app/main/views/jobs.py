# -*- coding: utf-8 -*-

from functools import partial

from flask import (
    Markup,
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
from notifications_utils.template import (
    EmailPreviewTemplate,
    LetterPreviewTemplate,
    SMSBodyPreviewTemplate,
)

from app import (
    current_service,
    format_datetime_short,
    format_thousands,
    notification_api_client,
    service_api_client,
)
from app.formatters import get_time_left, message_count_noun
from app.main import main
from app.main.forms import SearchNotificationsForm
from app.models.job import Job
from app.utils import parse_filter_args, set_status_filters
from app.utils.csv import generate_notifications_csv
from app.utils.letters import (
    get_letter_printing_statement,
    printing_today_or_tomorrow,
)
from app.utils.pagination import (
    generate_next_dict,
    generate_previous_dict,
    get_page_from_request,
)
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/jobs")
@user_has_permissions()
def view_jobs(service_id):
    return redirect(url_for(
        'main.uploads',
        service_id=current_service.id,
    ))


@main.route("/services/<uuid:service_id>/jobs/<uuid:job_id>")
@user_has_permissions()
def view_job(service_id, job_id):
    job = Job.from_id(job_id, service_id=current_service.id)
    if job.cancelled:
        abort(404)

    filter_args = parse_filter_args(request.args)
    filter_args['status'] = set_status_filters(filter_args)

    just_sent_message = 'Your {} been sent. Printing starts {} at 5:30pm.'.format(
        'letter has' if job.notification_count == 1 else 'letters have',
        printing_today_or_tomorrow(job.created_at)
    )

    return render_template(
        'views/jobs/job.html',
        job=job,
        status=request.args.get('status', ''),
        updates_url=url_for(
            ".view_job_updates",
            service_id=service_id,
            job_id=job.id,
            status=request.args.get('status', ''),
        ),
        partials=get_job_partials(job),
        just_sent=request.args.get('just_sent') == 'yes',
        just_sent_message=just_sent_message,
    )


@main.route("/services/<uuid:service_id>/jobs/<uuid:job_id>.csv")
@user_has_permissions('view_activity')
def view_job_csv(service_id, job_id):
    job = Job.from_id(job_id, service_id=service_id)
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
                template_type=job.template_type,
            )
        ),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'inline; filename="{} - {}.csv"'.format(
                job.template['name'],
                format_datetime_short(job.created_at)
            )
        }
    )


@main.route("/services/<uuid:service_id>/jobs/<uuid:job_id>", methods=['POST'])
@user_has_permissions('send_messages')
def cancel_job(service_id, job_id):
    Job.from_id(job_id, service_id=service_id).cancel()
    return redirect(url_for('main.service_dashboard', service_id=service_id))


@main.route("/services/<uuid:service_id>/jobs/<uuid:job_id>/cancel", methods=['GET', 'POST'])
@user_has_permissions()
def cancel_letter_job(service_id, job_id):
    if request.method == 'POST':
        job = Job.from_id(job_id, service_id=service_id)

        if job.status != 'finished' or job.notifications_created < job.notification_count:
            flash("We are still processing these letters, please try again in a minute.", 'try again')
            return view_job(service_id, job_id)
        try:
            number_of_letters = job.cancel()
        except HTTPError as e:
            flash(e.message, 'dangerous')
            return redirect(url_for('main.view_job', service_id=service_id, job_id=job_id))
        flash("Cancelled {} letters from {}".format(
            format_thousands(number_of_letters), job.original_file_name
        ), 'default_with_tick')
        return redirect(url_for('main.service_dashboard', service_id=service_id))

    flash("Are you sure you want to cancel sending these letters?", 'cancel')
    return view_job(service_id, job_id)


@main.route("/services/<uuid:service_id>/jobs/<uuid:job_id>.json")
@user_has_permissions()
def view_job_updates(service_id, job_id):

    job = Job.from_id(job_id, service_id=service_id)

    return jsonify(**get_job_partials(job))


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
        search_form=SearchNotificationsForm(
            message_type=message_type,
            to=request.form.get('to'),
        ),
        things_you_can_search_by={
            'email': ['email address'],
            'sms': ['phone number'],
            'letter': ['postal address', 'file name'],
            # We say recipient here because combining all 3 types, plus
            # reference gets too long for the hint text
            None: ['recipient'],
        }.get(message_type) + {
            True: ['reference'],
            False: [],
        }.get(bool(current_service.api_keys)),
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
    search_term = request.form.get('to', '')

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
        to=search_term,
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
            show_pagination=(not search_term),
            status=request.args.get('status'),
            message_type=message_type,
            download_link=download_link,
            single_notification_url=partial(
                url_for,
                '.view_notification',
                service_id=current_service.id,
            )
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
    job_type = job.template_type
    return [
        (
            label,
            query_param,
            url_for(
                ".view_job",
                service_id=job.service,
                job_id=job.id,
                status=query_param,
            ),
            count
        ) for label, query_param, count in [
            [
                Markup(
                    f'''total<span class="govuk-visually-hidden">
                    {"text message" if job_type == "sms" else job_type}s</span>'''
                ),
                '',
                job.notification_count
            ],
            [
                Markup(
                    f'''sending<span class="govuk-visually-hidden">
                    {message_count_noun(job.notifications_sending, job_type)}</span>'''
                ),
                'sending',
                job.notifications_sending
            ],
            [
                Markup(
                    f'''delivered<span class="govuk-visually-hidden">
                    {message_count_noun(job.notifications_delivered, job_type)}</span>'''
                ),
                'delivered',
                job.notifications_delivered
            ],
            [
                Markup(
                    f'''failed<span class="govuk-visually-hidden">
                    {message_count_noun(job.notifications_failed, job_type)}</span>'''
                ),
                'failed',
                job.notifications_failed
            ]
        ]
    ]


def get_job_partials(job):
    filter_args = parse_filter_args(request.args)
    filter_args['status'] = set_status_filters(filter_args)
    notifications = job.get_notifications(status=filter_args['status'])
    if job.template_type == 'letter':
        counts = render_template(
            'partials/jobs/count-letters.html',
            job=job,
        )
    else:
        counts = render_template(
            'partials/count.html',
            counts=_get_job_counts(job),
            status=filter_args['status'],
            notifications_deleted=(
                job.status == 'finished' and not notifications['notifications']
            ),
        )
    service_data_retention_days = current_service.get_days_of_retention(job.template_type)

    return {
        'counts': counts,
        'notifications': render_template(
            'partials/jobs/notifications.html',
            notifications=list(
                add_preview_of_content_to_notifications(notifications['notifications'])
            ),
            more_than_one_page=bool(notifications.get('links', {}).get('next')),
            download_link=url_for(
                '.view_job_csv',
                service_id=current_service.id,
                job_id=job.id,
                status=request.args.get('status')
            ),
            time_left=get_time_left(job.created_at, service_data_retention_days=service_data_retention_days),
            job=job,
            service_data_retention_days=service_data_retention_days,
        ),
        'status': render_template(
            'partials/jobs/status.html',
            job=job,
            letter_print_day=get_letter_printing_statement("created", job.created_at)
        ),
    }


def add_preview_of_content_to_notifications(notifications):

    for notification in notifications:
        yield(dict(
            preview_of_content=get_preview_of_content(notification),
            **notification
        ))


def get_preview_of_content(notification):

    if notification['template'].get('redact_personalisation'):
        notification['personalisation'] = {}

    if notification['template']['is_precompiled_letter']:
        return notification['client_reference']

    if notification['template']['template_type'] == 'sms':
        return str(SMSBodyPreviewTemplate(
            notification['template'],
            notification['personalisation'],
        ))

    if notification['template']['template_type'] == 'email':
        return Markup(EmailPreviewTemplate(
            notification['template'],
            notification['personalisation'],
            redact_missing_personalisation=True,
        ).subject)

    if notification['template']['template_type'] == 'letter':
        return Markup(LetterPreviewTemplate(
            notification['template'],
            notification['personalisation'],
        ).subject)

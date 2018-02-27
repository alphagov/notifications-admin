# -*- coding: utf-8 -*-
import base64
from collections import ItemsView
from datetime import datetime

from flask import (
    Response,
    abort,
    jsonify,
    render_template,
    request,
    stream_with_context,
    url_for,
)
from flask_login import login_required

from app import (
    current_service,
    format_date_numeric,
    job_api_client,
    notification_api_client,
)
from app.main import main
from app.template_previews import get_page_count_for_letter
from app.utils import (
    DELIVERED_STATUSES,
    FAILURE_STATUSES,
    generate_notifications_csv,
    get_help_argument,
    get_letter_timings,
    get_template,
    get_time_left,
    parse_filter_args,
    set_status_filters,
    user_has_permissions,
)


@main.route("/services/<service_id>/notification/<uuid:notification_id>")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_notification(service_id, notification_id):
    notification = notification_api_client.get_notification(service_id, str(notification_id))
    notification['template'].update({'reply_to_text': notification['reply_to_text']})

    template = get_template(
        notification['template'],
        current_service,
        letter_preview_url=url_for(
            '.view_letter_notification_as_preview',
            service_id=service_id,
            notification_id=notification_id,
            filetype='png',
        ),
        page_count=get_page_count_for_letter(notification['template']),
        show_recipient=True,
        redact_missing_personalisation=True,
    )
    template.values = get_all_personalisation_from_notification(notification)
    if notification['job']:
        job = job_api_client.get_job(service_id, notification['job']['id'])['data']
    else:
        job = None

    return render_template(
        'views/notifications/notification.html',
        finished=(notification['status'] in (DELIVERED_STATUSES + FAILURE_STATUSES)),
        uploaded_file_name='Report',
        template=template,
        job=job,
        updates_url=url_for(
            ".view_notification_updates",
            service_id=service_id,
            notification_id=notification['id'],
            status=request.args.get('status'),
            help=get_help_argument()
        ),
        partials=get_single_notification_partials(notification),
        created_by=notification.get('created_by'),
        created_at=notification['created_at'],
        help=get_help_argument(),
        estimated_letter_delivery_date=get_letter_timings(notification['created_at']).earliest_delivery,
        notification_id=notification['id'],
        can_receive_inbound=('inbound_sms' in current_service['permissions']),
    )


@main.route("/services/<service_id>/notification/<uuid:notification_id>.<filetype>")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_letter_notification_as_preview(service_id, notification_id, filetype):

    print("\n\nview_letter_notification_as_preview\n\n")

    if filetype not in ('pdf', 'png'):
        abort(404)

    notification = notification_api_client.get_notification(service_id, notification_id)
    notification['template'].update({'reply_to_text': notification['reply_to_text']})

    template = get_template(
        notification['template'],
        current_service,
        letter_preview_url=url_for(
            '.view_letter_notification_as_preview',
            service_id=service_id,
            notification_id=notification_id,
            filetype='png',
        ),
    )

    template.values = notification['personalisation']

    preview = notification_api_client.get_notification_letter_preview(
        service_id,
        template.id,
        notification_id,
        filetype,
        page=request.args.get('page')
    )

    return base64.b64decode(preview['content']), preview['status'], ItemsView(dict(preview['headers']))


@main.route("/services/<service_id>/notification/<notification_id>.json")
@user_has_permissions('view_activity', admin_override=True)
def view_notification_updates(service_id, notification_id):
    return jsonify(**get_single_notification_partials(
        notification_api_client.get_notification(service_id, notification_id)
    ))


def get_single_notification_partials(notification):
    return {
        'notifications': render_template(
            'partials/notifications/notifications.html',
            notification=notification,
            more_than_one_page=False,
            percentage_complete=100,
            time_left=get_time_left(notification['created_at']),
        ),
        'status': render_template(
            'partials/notifications/status.html',
            notification=notification
        ),
    }


def get_all_personalisation_from_notification(notification):

    if notification['template'].get('redact_personalisation'):
        notification['personalisation'] = {}

    if notification['template']['template_type'] == 'email':
        notification['personalisation']['email_address'] = notification['to']

    if notification['template']['template_type'] == 'sms':
        notification['personalisation']['phone_number'] = notification['to']

    return notification['personalisation']


@main.route("/services/<service_id>/download-notifications.csv")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def download_notifications_csv(service_id):
    filter_args = parse_filter_args(request.args)
    filter_args['status'] = set_status_filters(filter_args)

    return Response(
        stream_with_context(
            generate_notifications_csv(
                service_id=service_id,
                job_id=None,
                status=filter_args.get('status'),
                page=request.args.get('page', 1),
                page_size=5000,
                format_for_csv=True,
                template_type=filter_args.get('message_type')
            )
        ),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'inline; filename="{} - {} - {} report.csv"'.format(
                format_date_numeric(datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")),
                filter_args['message_type'][0],
                current_service['name'])
        }
    )

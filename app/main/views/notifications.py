# -*- coding: utf-8 -*-
from flask import (
    render_template,
    jsonify,
    request,
    url_for,
    current_app
)
from flask_login import login_required

from app import (
    notification_api_client,
    current_service
)
from app.main import main
from app.utils import (
    user_has_permissions,
    get_help_argument,
    get_template,
    get_time_left,
    REQUESTED_STATUSES,
    FAILURE_STATUSES,
    SENDING_STATUSES,
    DELIVERED_STATUSES,
)


def get_status_arg(filter_args):
    if 'status' not in filter_args or not filter_args['status']:
        return REQUESTED_STATUSES
    elif filter_args['status'] == 'sending':
        return SENDING_STATUSES
    elif filter_args['status'] == 'delivered':
        return DELIVERED_STATUSES
    elif filter_args['status'] == 'failed':
        return FAILURE_STATUSES
    else:
        current_app.logger.info('Unrecognised status filter: {}'.format(filter_args['status']))
        return REQUESTED_STATUSES


@main.route("/services/<service_id>/notification/<notification_id>")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_notification(service_id, notification_id):
    notification = notification_api_client.get_notification(service_id, notification_id)
    return render_template(
        'views/notifications/notification.html',
        finished=(notification['status'] in (DELIVERED_STATUSES + FAILURE_STATUSES)),
        uploaded_file_name='Report',
        template=get_template(
            notification['template'],
            current_service,
            letter_preview_url=url_for(
                '.view_template_version_preview',
                service_id=service_id,
                template_id=notification['template']['id'],
                version=notification['template_version'],
                filetype='png',
            ),
        ),
        status=request.args.get('status'),
        updates_url=url_for(
            ".view_notification_updates",
            service_id=service_id,
            notification_id=notification['id'],
            status=request.args.get('status'),
            help=get_help_argument()
        ),
        partials=get_single_notification_partials(notification),
        help=get_help_argument()
    )


@main.route("/services/<service_id>/notification/<notification_id>.json")
@user_has_permissions('view_activity', admin_override=True)
def view_notification_updates(service_id, notification_id):
    return jsonify(**get_single_notification_partials(
        notification_api_client.get_notification(service_id, notification_id)
    ))


def _get_single_notification_counts(notification, help_argument):
    return [
        (
            label,
            query_param,
            url_for(
                ".view_notification",
                service_id=notification['service'],
                notification_id=notification['id'],
                status=query_param,
                help=help_argument
            ),
            count
        ) for label, query_param, count in [
            [
                'total', '',
                1
            ],
            [
                'sending', 'sending',
                int(notification['status'] in SENDING_STATUSES)
            ],
            [
                'delivered', 'delivered',
                int(notification['status'] in DELIVERED_STATUSES)
            ],
            [
                'failed', 'failed',
                int(notification['status'] in FAILURE_STATUSES)
            ]
        ]
    ]


def get_single_notification_partials(notification):
    status_args = get_status_arg(request.args)

    return {
        'counts': render_template(
            'partials/count.html',
            counts=_get_single_notification_counts(notification, request.args.get('help', 0)),
            status=status_args
        ),
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

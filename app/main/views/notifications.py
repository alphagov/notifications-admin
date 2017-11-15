# -*- coding: utf-8 -*-
from flask import (
    render_template,
    jsonify,
    request,
    url_for,
)
from flask_login import login_required

from app import (
    notification_api_client,
    job_api_client,
    current_service
)
from app.main import main
from app.template_previews import TemplatePreview
from app.utils import (
    user_has_permissions,
    get_help_argument,
    get_template,
    get_time_left,
    get_letter_timings,
    FAILURE_STATUSES,
    DELIVERED_STATUSES,
)


@main.route("/services/<service_id>/notification/<uuid:notification_id>")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_notification(service_id, notification_id):
    notification = notification_api_client.get_notification(service_id, str(notification_id))
    template = get_template(
        notification['template'],
        current_service,
        letter_preview_url=url_for(
            '.view_letter_notification_as_image',
            service_id=service_id,
            notification_id=notification_id,
        ),
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


@main.route("/services/<service_id>/notification/<uuid:notification_id>.png")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def view_letter_notification_as_image(service_id, notification_id):

    notification = notification_api_client.get_notification(service_id, notification_id)

    template = get_template(
        notification['template'],
        current_service,
        letter_preview_url=url_for(
            '.view_letter_notification_as_image',
            service_id=service_id,
            notification_id=notification_id,
        ),
    )

    template.values = notification['personalisation']

    return TemplatePreview.from_utils_template(template, 'png', page=request.args.get('page'))


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

from flask import (
    jsonify,
    render_template,
    url_for,
)
from flask_login import login_required
from notifications_utils.recipients import format_phone_number_human_readable
from notifications_utils.template import SMSPreviewTemplate
from app.main import main
from app.utils import user_has_permissions
from app import notification_api_client, service_api_client
from notifications_python_client.errors import HTTPError


@main.route("/services/<service_id>/conversation/<notification_id>")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def conversation(service_id, notification_id):

    user_number = get_user_number(service_id, notification_id)

    return render_template(
        'views/conversations/conversation.html',
        user_number=user_number,
        partials=get_conversation_partials(service_id, user_number),
        updates_url=url_for('.conversation_updates', service_id=service_id, notification_id=notification_id),
    )


@main.route("/services/<service_id>/conversation/<notification_id>.json")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def conversation_updates(service_id, notification_id):

    return jsonify(get_conversation_partials(
        service_id,
        get_user_number(service_id, notification_id)
    ))


def get_conversation_partials(service_id, user_number):

    return {
        'messages': render_template(
            'views/conversations/messages.html',
            conversation=get_sms_thread(service_id, user_number),
        )
    }


def get_user_number(service_id, notification_id):
    try:
        user_number = service_api_client.get_inbound_sms_by_id(service_id, notification_id)['user_number']
    except HTTPError:
        user_number = notification_api_client.get_notification(service_id, notification_id)['to']
    return format_phone_number_human_readable(user_number)


def get_sms_thread(service_id, user_number):

    for notification in sorted((
        notification_api_client.get_notifications_for_service(service_id, to=user_number)['notifications'] +
        service_api_client.get_inbound_sms(service_id, user_number=user_number)
    ), key=lambda notification: notification['created_at']):

        is_inbound = ('notify_number' in notification)
        redact_personalisation = not is_inbound and notification['template']['redact_personalisation']

        if redact_personalisation:
            notification['personalisation'] = {}

        yield {
            'inbound': is_inbound,
            'content': SMSPreviewTemplate(
                {
                    'content': (
                        notification['content'] if is_inbound else
                        notification['template']['content']
                    )
                },
                notification.get('personalisation'),
                downgrade_non_gsm_characters=(not is_inbound),
                redact_missing_personalisation=redact_personalisation,
            ),
            'created_at': notification['created_at'],
            'status': notification.get('status'),
            'id': notification['id'],
        }

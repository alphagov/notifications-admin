from flask import jsonify, redirect, render_template, session, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError
from notifications_utils.recipients import format_phone_number_human_readable
from notifications_utils.template import SMSPreviewTemplate

from app import current_service, service_api_client
from app.main import main
from app.main.forms import SearchByNameForm
from app.models.notification import Notification, Notifications
from app.models.template_list import TemplateList
from app.utils import user_has_permissions


@main.route("/services/<uuid:service_id>/conversation/<uuid:notification_id>")
@user_has_permissions('view_activity')
def conversation(service_id, notification_id):

    user_number = get_user_number(service_id, notification_id)

    return render_template(
        'views/conversations/conversation.html',
        user_number=user_number,
        partials=get_conversation_partials(service_id, user_number),
        updates_url=url_for('.conversation_updates', service_id=service_id, notification_id=notification_id),
        notification_id=notification_id,
    )


@main.route("/services/<uuid:service_id>/conversation/<uuid:notification_id>.json")
@user_has_permissions('view_activity')
def conversation_updates(service_id, notification_id):

    return jsonify(get_conversation_partials(
        service_id,
        get_user_number(service_id, notification_id)
    ))


@main.route("/services/<uuid:service_id>/conversation/<uuid:notification_id>/reply-with")
@main.route("/services/<uuid:service_id>/conversation/<uuid:notification_id>/reply-with/from-folder/<uuid:from_folder>")
@user_has_permissions('send_messages')
def conversation_reply(
    service_id,
    notification_id,
    from_folder=None,
):
    return render_template(
        'views/templates/choose-reply.html',
        templates_and_folders=TemplateList(
            current_service,
            template_folder_id=from_folder,
            user=current_user,
            template_type='sms'
        ),
        template_folder_path=current_service.get_template_folder_path(from_folder),
        search_form=SearchByNameForm(),
        notification_id=notification_id,
        template_type='sms'
    )


@main.route("/services/<uuid:service_id>/conversation/<uuid:notification_id>/reply-with/<uuid:template_id>")
@user_has_permissions('send_messages')
def conversation_reply_with_template(
    service_id,
    notification_id,
    template_id,
):

    session['recipient'] = get_user_number(service_id, notification_id)
    session['placeholders'] = {'phone number': session['recipient']}

    return redirect(url_for(
        'main.send_one_off_step',
        service_id=service_id,
        template_id=template_id,
        step_index=1,
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
    except HTTPError as e:
        if e.status_code != 404:
            raise
        user_number = Notification.from_id(notification_id, service_id).to
    return format_phone_number_human_readable(user_number)


def get_sms_thread(service_id, user_number):

    for notification in sorted((
        Notifications(
            service_id,
            to=user_number,
            template_type='sms',
        ) +
        service_api_client.get_inbound_sms(service_id, user_number=user_number)['data']
    ), key=lambda notification: (
        notification.created_at.isoformat()
        if isinstance(notification, Notification)
        else notification['created_at']
    )):

        is_inbound = not isinstance(notification, Notification)
        created_at = notification['created_at'] if is_inbound else notification.created_at
        status = None if is_inbound else notification.status
        redact_personalisation = not is_inbound and notification.redact_personalisation
        id = notification['id'] if is_inbound else notification.id

        yield {
            'inbound': is_inbound,
            'content': SMSPreviewTemplate(
                {
                    'content': (
                        notification['content'] if is_inbound else
                        notification.template['content']
                    )
                },
                None if is_inbound else notification.personalisation,
                downgrade_non_sms_characters=(not is_inbound),
                redact_missing_personalisation=redact_personalisation,
            ),
            'created_at': created_at,
            'status': status,
            'id': id,
        }

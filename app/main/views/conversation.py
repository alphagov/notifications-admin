from flask import jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError
from notifications_utils.template import SMSPreviewTemplate

from app import current_service, notification_api_client, service_api_client
from app.main import json_updates, main
from app.main.forms import SearchByNameForm
from app.models.notification import InboundSMSMessage, InboundSMSMessages, Notifications
from app.models.template_list import UserTemplateList
from app.utils.user import user_has_permissions
from app.utils.validation import format_phone_number_human_readable


@main.route("/services/<uuid:service_id>/conversation/<uuid:notification_id>")
@user_has_permissions("view_activity")
def conversation(service_id, notification_id):
    user_number = get_user_number(service_id, notification_id)

    return render_template(
        "views/conversations/conversation.html",
        user_number=user_number,
        partials=get_conversation_partials(service_id, user_number),
        updates_url=url_for(
            "json_updates.conversation_updates", service_id=service_id, notification_id=notification_id
        ),
        notification_id=notification_id,
    )


@json_updates.route("/services/<uuid:service_id>/conversation/<uuid:notification_id>.json")
@user_has_permissions("view_activity")
def conversation_updates(service_id, notification_id):
    return jsonify(get_conversation_partials(service_id, get_user_number(service_id, notification_id)))


@main.route("/services/<uuid:service_id>/conversation/<uuid:notification_id>/reply-with")
@main.route("/services/<uuid:service_id>/conversation/<uuid:notification_id>/reply-with/from-folder/<uuid:from_folder>")
@user_has_permissions("send_messages")
def conversation_reply(
    service_id,
    notification_id,
    from_folder=None,
):
    if from_folder:
        parent_folder_id = current_service.get_template_folder(from_folder)["parent_id"]
        back_link = url_for(
            "main.conversation_reply",
            service_id=service_id,
            notification_id=notification_id,
            from_folder=parent_folder_id,
        )
    else:
        back_link = url_for("main.conversation", service_id=service_id, notification_id=notification_id)

    return render_template(
        "views/templates/choose-reply.html",
        templates_and_folders=UserTemplateList(
            service=current_service, template_folder_id=from_folder, user=current_user, template_type="sms"
        ),
        template_folder_path=current_service.get_template_folder_path(from_folder),
        from_folder=from_folder,
        _search_form=SearchByNameForm(),
        notification_id=notification_id,
        template_type="sms",
        back_link=back_link,
    )


@main.route("/services/<uuid:service_id>/conversation/<uuid:notification_id>/reply-with/<uuid:template_id>")
@user_has_permissions("send_messages")
def conversation_reply_with_template(
    service_id,
    notification_id,
    template_id,
):
    session["recipient"] = get_user_number(service_id, notification_id)
    session["placeholders"] = {"phone number": session["recipient"]}
    session["from_inbound_sms_details"] = {
        "notification_id": notification_id,
        "from_folder": request.args.get("from_folder"),
    }

    return redirect(
        url_for(
            "main.send_one_off_step",
            service_id=service_id,
            template_id=template_id,
            step_index=1,
        )
    )


def get_conversation_partials(service_id, user_number):
    return {
        "messages": render_template(
            "views/conversations/messages.html",
            conversation=get_sms_thread(service_id, user_number),
        )
    }


def get_user_number(service_id, notification_id):
    try:
        user_number = service_api_client.get_inbound_sms_by_id(service_id, notification_id)["user_number"]
    except HTTPError as e:
        if e.status_code != 404:
            raise
        user_number = notification_api_client.get_notification(service_id, notification_id)["to"]
    return format_phone_number_human_readable(user_number)


def get_sms_thread(service_id, user_number):
    for notification in sorted(
        Notifications(service_id, to=user_number, template_type="sms")
        + InboundSMSMessages(service_id, user_number=user_number)
    ):
        is_inbound = isinstance(notification, InboundSMSMessage)

        yield {
            "inbound": is_inbound,
            "content": SMSPreviewTemplate(
                {
                    "template_type": "sms",
                    "content": notification.content,
                },
                notification.personalisation,
                downgrade_non_sms_characters=(not is_inbound),
                redact_missing_personalisation=notification.redact_personalisation,
            ),
            "created_at": notification.created_at,
            "status": notification.status,
            "id": notification.id,
        }

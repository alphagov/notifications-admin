from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user
from notifications_utils.clients.zendesk.zendesk_client import NotifySupportTicket, NotifyTicketType

from app import current_service
from app.extensions import zendesk_client
from app.main import main
from app.utils.user import user_has_permissions, user_is_gov_user


@main.route("/services/<uuid:service_id>/service-settings/request-to-go-live", methods=["GET"])
@user_has_permissions("manage_service")
def request_to_go_live(service_id):
    if current_service.live:
        return render_template("views/service-settings/service-already-live.html", prompt_to_switch_service=True)

    return render_template("views/service-settings/request-to-go-live.html")


@main.route("/services/<uuid:service_id>/service-settings/request-to-go-live", methods=["POST"])
@user_has_permissions("manage_service")
@user_is_gov_user
def submit_request_to_go_live(service_id):
    if (not current_service.go_live_checklist_completed) or (
        current_service.able_to_accept_agreement and not current_service.organisation.agreement_signed
    ):
        abort(403)

    ticket_message = render_template("support-tickets/go-live-request.txt") + "\n"
    if current_service.organisation.can_approve_own_go_live_requests:
        subject = f"Self approve go live request - {current_service.name}"
        notify_task_type = "notify_task_go_live_request_self_approve"
    else:
        subject = f"Request to go live - {current_service.name}"
        notify_task_type = "notify_task_go_live_request"

    ticket = NotifySupportTicket(
        subject=subject,
        message=ticket_message,
        ticket_type=NotifySupportTicket.TYPE_TASK,
        notify_ticket_type=NotifyTicketType.NON_TECHNICAL,
        user_name=current_user.name,
        user_email=current_user.email_address,
        requester_sees_message_content=False,
        org_id=current_service.organisation_id,
        org_type=current_service.organisation_type,
        service_id=current_service.id,
        notify_task_type=notify_task_type,
        user_created_at=current_user.created_at,
    )
    zendesk_client.send_ticket_to_zendesk(ticket)

    current_service.update(
        go_live_user=current_user.id,
        has_active_go_live_request=True,
    )

    current_service.notify_organisation_users_of_request_to_go_live()

    flash("Thanks for your request to go live. We’ll get back to you within one working day.", "default")
    return redirect(url_for(".service_settings", service_id=service_id))

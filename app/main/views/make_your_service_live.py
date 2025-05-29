from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError
from notifications_utils.clients.zendesk.zendesk_client import NotifySupportTicket, NotifyTicketType

from app import current_service, service_api_client
from app.extensions import zendesk_client
from app.main import main
from app.main.forms import RenameServiceForm
from app.utils.user import user_has_permissions, user_is_gov_user


@main.route("/services/<uuid:service_id>/make-your-service-live", methods=["GET"])
@user_has_permissions("manage_service")
def request_to_go_live(service_id):
    if current_service.live:
        return render_template("views/service-already-live.html", prompt_to_switch_service=True)

    return render_template("views/request-to-go-live.html")


@main.route("/services/<uuid:service_id>/make-your-service-live", methods=["POST"])
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
    # current_service.update won’t modify itself, it only makes a request to the API and returns the JSON response
    # https://github.com/alphagov/notifications-admin/blob/main/app/models/service.py#L103-L104
    # so what you have in memory will be whatever the state of the service was before calling update
    # we do this because usually post-redirect-get is a better way to do things
    # after the redirect, GET request gets a fresh copy of the JSON from the API
    return redirect(url_for(".request_to_go_live", service_id=service_id))


@main.route("/services/<uuid:service_id>/make-your-service-live/confirm-service-unique", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def confirm_service_is_unique(service_id):
    form = RenameServiceForm(name=current_service.name)
    back_link = url_for(".request_to_go_live", service_id=service_id)

    if form.validate_on_submit():
        try:
            current_service.update(name=form.name.data, confirmed_unique=True)
        except HTTPError as http_error:
            if http_error.status_code == 400 and (
                error_message := service_api_client.parse_edit_service_http_error(http_error)
            ):
                form.name.errors.append(error_message)
            else:
                raise http_error
        else:
            return redirect(back_link)

    return render_template(
        "views/confirm-your-service-is-unique.html",
        form=form,
        back_link=back_link,
        error_summary_enabled=True,
    )

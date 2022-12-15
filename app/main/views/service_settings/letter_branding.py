from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user
from notifications_utils.clients.zendesk.zendesk_client import NotifySupportTicket

from app import current_service
from app.extensions import zendesk_client
from app.main import main
from app.main.forms import ChooseLetterBrandingForm
from app.utils.user import user_has_permissions

from .index import THANKS_FOR_BRANDING_REQUEST_MESSAGE


@main.route("/services/<uuid:service_id>/service-settings/letter-branding", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def letter_branding_request(service_id):
    form = ChooseLetterBrandingForm(current_service)
    from_template = request.args.get("from_template")
    if form.validate_on_submit():
        branding_choice = form.options.data

        if branding_choice in current_service.letter_branding_pool.ids:
            return redirect(
                url_for(".letter_branding_pool_option", service_id=current_service.id, branding_option=branding_choice)
            )

        ticket_message = render_template(
            "support-tickets/branding-request.txt",
            current_branding=current_service.letter_branding.name or "no",
            branding_requested=dict(form.options.choices)[form.options.data],
            detail=form.something_else.data,
        )
        ticket = NotifySupportTicket(
            subject=f"Letter branding request - {current_service.name}",
            message=ticket_message,
            ticket_type=NotifySupportTicket.TYPE_QUESTION,
            user_name=current_user.name,
            user_email=current_user.email_address,
            org_id=current_service.organisation_id,
            org_type=current_service.organisation_type,
            service_id=current_service.id,
        )
        zendesk_client.send_ticket_to_zendesk(ticket)
        flash((THANKS_FOR_BRANDING_REQUEST_MESSAGE), "default")
        return redirect(
            url_for(".view_template", service_id=current_service.id, template_id=from_template)
            if from_template
            else url_for(".service_settings", service_id=current_service.id)
        )

    return render_template(
        "views/service-settings/branding/letter-branding-options.html",
        form=form,
        from_template=from_template,
    )


@main.route("/services/<uuid:service_id>/service-settings/letter-branding/pool", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def letter_branding_pool_option(service_id):
    try:
        chosen_branding = current_service.letter_branding_pool.get_item_by_id(request.args.get("branding_option"))
    except current_service.letter_branding_pool.NotFound:
        flash("No branding found for this id.")
        return redirect(url_for(".letter_branding_request", service_id=current_service.id))

    if request.method == "POST":
        current_service.update(letter_branding=chosen_branding.id)

        flash("You’ve updated your letter branding", "default")
        return redirect(url_for(".service_settings", service_id=current_service.id))

    return render_template(
        "views/service-settings/branding/letter-branding-pool-option.html",
        chosen_branding=chosen_branding,
    )

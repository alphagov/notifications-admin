import uuid

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from notifications_utils.clients.zendesk.zendesk_client import NotifySupportTicket

from app import current_service
from app.extensions import zendesk_client
from app.main import main
from app.main.forms import ChooseLetterBrandingForm, LetterBrandingUploadBranding
from app.s3_client.s3_logo_client import upload_letter_temp_logo
from app.utils.user import user_has_permissions

from .index import THANKS_FOR_BRANDING_REQUEST_MESSAGE


def _letter_branding_flow_query_params(**kwargs):
    """Return a dictionary containing values for the letter branding flow.

    We've got a variety of query parameters we want to pass around between pages. Any params that are passed in, we
    should pass through to ensure that back links continue to work the whole way through etc. In addition, we use the
    branding_choice param (from the letter_branding_request page) later on so need to pass that through.

    To set a new value:
        _letter_branding_flow_query_params(request, branding_choice='organisation')

    To remove a value:
        _letter_branding_flow_query_params(request, branding_choice=None)
    """
    return {k: kwargs.get(k, request.args.get(k)) for k in ("from_template", "branding_choice")}


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

        # TODO: when the upload flow is ready:
        # remove the platform admin check here
        # remove the zendesk stuff from here
        # remove the textbox that is hidden under the something else option from the form
        # clean up the tests to remove all reference to the "something_else" field
        if current_user.platform_admin:
            return redirect(
                url_for(
                    ".letter_branding_upload_branding",
                    service_id=current_service.id,
                    **_letter_branding_flow_query_params(branding_choice=branding_choice),
                )
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


@main.route("/services/<uuid:service_id>/service-settings/letter-branding/upload-branding", methods=["GET", "POST"])
def letter_branding_upload_branding(service_id):
    form = LetterBrandingUploadBranding()
    if form.validate_on_submit():
        # We don't need to care about the filename as we're providing a UUID. This filename is never used to represent
        # the branding again so we don't need to capture what the file on disk was called
        filename = "branding.svg"
        upload_id = str(uuid.uuid4())
        branding_filename = upload_letter_temp_logo(
            filename,
            form.branding.data.read(),
            current_app.config["AWS_REGION"],
            user_id=current_user.id,
            unique_id=upload_id,
        )

        # TODO: redirect to the next step of the flow instead (passing through the params)
        return redirect(f"https://{current_app.config['LOGO_CDN_DOMAIN']}/{branding_filename}")

    return render_template(
        "views/service-settings/branding/add-new-branding/letter-branding-upload-branding.html",
        form=form,
        branding_choice=request.args.get("branding_choice"),
        back_link=url_for(
            ".letter_branding_request",
            service_id=current_service.id,
            **_letter_branding_flow_query_params(branding_choice=None),
        ),
        # TODO: Create branding-specific zendesk flow that creates branding ticket (see .letter_branding_request)
        abandon_flow_link=url_for(".support"),
    )

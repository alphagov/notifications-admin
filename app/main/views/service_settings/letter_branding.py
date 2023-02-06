from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from notifications_utils.clients.zendesk.zendesk_client import NotifySupportTicket

from app import (
    current_service,
    letter_branding_client,
    logo_client,
    organisations_client,
)
from app.extensions import zendesk_client
from app.main import main
from app.main.forms import (
    ChooseLetterBrandingForm,
    LetterBrandingNameForm,
    LetterBrandingUploadBranding,
    SomethingElseBrandingForm,
)
from app.models.branding import LetterBranding
from app.utils.branding import get_letter_choices as get_letter_branding_choices
from app.utils.branding import letter_filename_for_db_from_logo_key
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
    return {k: kwargs.get(k, request.args.get(k)) for k in ("from_template", "branding_choice", "temp_filename")}


@main.route("/services/<uuid:service_id>/service-settings/letter-branding", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def letter_branding_request(service_id):
    form = ChooseLetterBrandingForm(current_service)
    from_template = request.args.get("from_template")

    if form.validate_on_submit():
        branding_choice = form.options.data

        if branding_choice == LetterBranding.NHS_ID:
            return redirect(
                url_for(
                    ".letter_branding_nhs",
                    service_id=current_service.id,
                )
            )

        if branding_choice in current_service.letter_branding_pool.ids:
            return redirect(
                url_for(".letter_branding_pool_option", service_id=current_service.id, branding_option=branding_choice)
            )

        return redirect(
            url_for(
                ".letter_branding_upload_branding",
                service_id=current_service.id,
                **_letter_branding_flow_query_params(branding_choice=branding_choice),
            )
        )

    return render_template(
        "views/service-settings/branding/letter-branding-options.html",
        form=form,
        from_template=from_template,
    )


@main.route("/services/<uuid:service_id>/service-settings/letter-branding/something-else", methods=["GET", "POST"])
def letter_branding_something_else(service_id):
    form = SomethingElseBrandingForm()
    from_template = _letter_branding_flow_query_params()["from_template"]

    if form.validate_on_submit():
        ticket_message = render_template(
            "support-tickets/branding-request.txt",
            current_branding=current_service.letter_branding.name or "no",
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
        "views/service-settings/branding/branding-something-else.html",
        form=form,
        from_template=from_template,
        back_link=url_for(
            ".letter_branding_upload_branding",
            service_id=current_service.id,
            **_letter_branding_flow_query_params(),
        ),
    )


def check_letter_branding_allowed_for_service(branding):
    allowed_branding_for_service = dict(get_letter_branding_choices(current_service))

    if branding not in allowed_branding_for_service:
        abort(404)


@main.route("/services/<uuid:service_id>/service-settings/letter-branding/nhs", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def letter_branding_nhs(service_id):
    check_letter_branding_allowed_for_service(LetterBranding.NHS_ID)

    if request.method == "POST":
        current_service.update(letter_branding=LetterBranding.NHS_ID)

        flash("You’ve updated your letter branding", "default")
        return redirect(url_for(".service_settings", service_id=current_service.id))

    return render_template(
        "views/service-settings/branding/letter-branding-nhs.html", nhs_branding_id=LetterBranding.NHS_ID
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
        temporary_logo_key = logo_client.save_temporary_logo(
            form.branding.data,
            logo_type="letter",
        )
        return redirect(
            url_for(
                "main.letter_branding_set_name",
                service_id=current_service.id,
                **_letter_branding_flow_query_params(temp_filename=temporary_logo_key),
            )
        )

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
        abandon_flow_link=url_for(".letter_branding_something_else", service_id=current_service.id),
    )


def _should_set_default_org_letter_branding(branding_choice):
    # 1. the user has chosen ‘[organisation name]’ in the first page of the journey
    user_chose_org_name = branding_choice == "organisation"
    # 2. and the organisation doesn’t have default branding already
    org_doesnt_have_default_branding = current_service.organisation.letter_branding_id is None
    # 3. and the organisation has no other live services
    no_other_live_services_in_org = not any(
        service.id != current_service.id for service in current_service.organisation.live_services
    )

    return user_chose_org_name and org_doesnt_have_default_branding and no_other_live_services_in_org


@main.route("/services/<uuid:service_id>/service-settings/letter-branding/set-name", methods=["GET", "POST"])
def letter_branding_set_name(service_id):
    letter_branding_data = _letter_branding_flow_query_params()
    temporary_logo_key = letter_branding_data["temp_filename"]

    if not temporary_logo_key:
        return redirect(url_for("main.letter_branding_upload_branding", service_id=service_id, **letter_branding_data))

    form = LetterBrandingNameForm()

    if form.validate_on_submit():
        name = letter_branding_client.get_unique_name_for_letter_branding(form.name.data)

        permanent_logo_key = logo_client.save_permanent_logo(
            temporary_logo_key, logo_type="letter", logo_key_extra=name
        )

        new_letter_branding = LetterBranding.create(
            name=name, filename=letter_filename_for_db_from_logo_key(permanent_logo_key)
        )

        # set as service branding
        current_service.update(letter_branding=new_letter_branding.id)

        # add to org pool
        organisations_client.add_brandings_to_letter_branding_pool(
            current_service.organisation.id, [new_letter_branding.id]
        )

        if _should_set_default_org_letter_branding(letter_branding_data["branding_choice"]):
            current_service.organisation.update(letter_branding_id=new_letter_branding.id, delete_services_cache=True)

        flash("You’ve changed your letter branding.", "default_with_tick")

        return redirect(url_for("main.service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/branding/add-new-branding/letter-branding-set-name.html",
        back_link=url_for(
            ".letter_branding_upload_branding",
            service_id=service_id,
            **_letter_branding_flow_query_params(temp_filename=None),
        ),
        temp_filename=letter_filename_for_db_from_logo_key(temporary_logo_key),
        form=form,
    )

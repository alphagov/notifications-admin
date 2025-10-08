from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from notifications_utils.clients.zendesk.zendesk_client import NotifySupportTicket, NotifyTicketType

from app import (
    current_service,
    letter_branding_client,
    logo_client,
    organisations_client,
)
from app.extensions import zendesk_client
from app.main import main
from app.main.forms import (
    BrandingRequestForm,
    ChooseEmailBrandingForm,
    ChooseLetterBrandingForm,
    EmailBrandingAltTextForm,
    EmailBrandingChooseBanner,
    EmailBrandingChooseBannerColour,
    EmailBrandingChooseLogoForm,
    EmailBrandingLogoUpload,
    GovernmentIdentityLogoForm,
    LetterBrandingNameForm,
    LetterBrandingUploadBranding,
)
from app.models.branding import AllEmailBranding, EmailBranding, LetterBranding
from app.models.organisation import Organisation
from app.utils import service_belongs_to_org_type
from app.utils.branding import get_email_choices as get_email_branding_choices
from app.utils.branding import get_letter_choices as get_letter_branding_choices
from app.utils.branding import letter_filename_for_db_from_logo_key
from app.utils.user import user_has_permissions

from .index import THANKS_FOR_BRANDING_REQUEST_MESSAGE

# ================= EMAIL BRANDING ==================


def create_email_branding_zendesk_ticket(detail=None):
    ticket_message = render_template(
        "support-tickets/branding-request.txt",
        current_branding=current_service.email_branding.name,
        detail=detail,
    )
    ticket = NotifySupportTicket(
        subject=f"Email branding request - {current_service.name}",
        message=ticket_message,
        ticket_type=NotifySupportTicket.TYPE_TASK,
        notify_ticket_type=NotifyTicketType.NON_TECHNICAL,
        user_name=current_user.name,
        user_email=current_user.email_address,
        org_id=current_service.organisation_id,
        org_type=current_service.organisation_type,
        service_id=current_service.id,
        notify_task_type="notify_task_email_branding",
        user_created_at=current_user.created_at,
    )
    zendesk_client.send_ticket_to_zendesk(ticket)


@main.route("/services/<uuid:service_id>/service-settings/email-branding", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def email_branding_options(service_id):
    form = ChooseEmailBrandingForm(current_service)
    form.options.data = form.options.data or request.args.get("branding_choice")

    if form.validate_on_submit():
        branding_choice = form.options.data

        if branding_choice == EmailBranding.NHS_ID:
            return redirect(
                url_for(
                    ".branding_nhs",
                    service_id=current_service.id,
                    branding_type="email",
                    branding_choice=branding_choice,
                )
            )
        elif branding_choice == "govuk":
            return redirect(
                url_for(".email_branding_govuk", service_id=current_service.id, branding_choice=branding_choice)
            )

        elif branding_choice in current_service.email_branding_pool.ids:
            return redirect(
                url_for(
                    ".branding_option_preview",
                    service_id=current_service.id,
                    branding_choice=branding_choice,
                    branding_type="email",
                )
            )

        elif current_service.organisation_type == "central":
            return redirect(
                url_for(".email_branding_choose_logo", service_id=current_service.id, branding_choice=branding_choice)
            )

        return redirect(
            url_for(
                ".email_branding_choose_banner_type",
                service_id=current_service.id,
                back_link=".email_branding_options",
                branding_choice=branding_choice,
            )
        )

    return render_template(
        "views/service-settings/branding/email-branding-options.html", form=form, error_summary_enabled=True
    )


def check_branding_allowed_for_service(branding, branding_type):
    if branding_type == "email":
        allowed_branding_for_service = dict(get_email_branding_choices(current_service))
    else:
        allowed_branding_for_service = dict(get_letter_branding_choices(current_service))

    if branding not in allowed_branding_for_service:
        abort(404)


@main.route("/services/<uuid:service_id>/service-settings/email-branding/govuk", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def email_branding_govuk(service_id):
    check_branding_allowed_for_service("govuk", branding_type="email")

    if request.method == "POST":
        current_service.update(email_branding=None)

        flash("You’ve updated your email branding", "default")
        return redirect(url_for(".service_settings", service_id=current_service.id))

    return render_template(
        "views/service-settings/branding/email-branding-govuk.html",
        back_link=url_for(
            "main.email_branding_options", service_id=current_service.id, **_email_branding_flow_query_params(request)
        ),
    )


@main.route("/services/<uuid:service_id>/service-settings/email-branding/request", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def email_branding_request(service_id):
    form = BrandingRequestForm()

    if form.validate_on_submit():
        create_email_branding_zendesk_ticket(detail=form.branding_request.data)

        flash(THANKS_FOR_BRANDING_REQUEST_MESSAGE, "default")
        return redirect(url_for(".service_settings", service_id=current_service.id))

    branding_options = ChooseEmailBrandingForm(current_service)
    default_back_view = (
        ".service_settings" if branding_options.something_else_is_only_option else ".email_branding_options"
    )
    back_link = url_for(
        request.args.get("back_link", default_back_view),
        service_id=current_service.id,
        **_email_branding_flow_query_params(request),
    )
    return render_template(
        "views/service-settings/branding/branding-request.html",
        form=form,
        back_link=back_link,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/email-branding/request-government-identity-logo",
    methods=["GET"],
)
@user_has_permissions("manage_service")
@service_belongs_to_org_type("central")
def email_branding_request_government_identity_logo(service_id):
    branding_choice = request.args.get("branding_choice")
    logo_type = request.args.get("logo_type")

    return render_template(
        "views/service-settings/branding/new/email-branding-create-government-identity-logo.html",
        service_id=service_id,
        back_link=url_for(
            ".email_branding_choose_logo",
            service_id=service_id,
            **_email_branding_flow_query_params(request),
        ),
        branding_choice=branding_choice,
        logo_type=logo_type,
        example=AllEmailBranding().example_government_identity_branding,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/email-branding/request-government-identity-logo/enter-text",
    methods=["GET", "POST"],
)
@user_has_permissions("manage_service")
@service_belongs_to_org_type("central")
def email_branding_enter_government_identity_logo_text(service_id):
    form = GovernmentIdentityLogoForm()
    branding_choice = request.args.get("branding_choice")

    if form.validate_on_submit():
        ticket_message = render_template(
            "support-tickets/government-logo-branding-request.txt",
            logo_text=form.logo_text.data,
            branding_choice=branding_choice,
        )
        ticket = NotifySupportTicket(
            subject=f"Email branding request - {current_service.name}",
            message=ticket_message,
            ticket_type=NotifySupportTicket.TYPE_TASK,
            notify_ticket_type=NotifyTicketType.NON_TECHNICAL,
            user_name=current_user.name,
            user_email=current_user.email_address,
            org_id=current_service.organisation_id,
            org_type=current_service.organisation_type,
            service_id=current_service.id,
            notify_task_type="notify_task_email_branding_gov",
            user_created_at=current_user.created_at,
        )
        zendesk_client.send_ticket_to_zendesk(ticket)
        flash((THANKS_FOR_BRANDING_REQUEST_MESSAGE), "default")
        return redirect(url_for(".service_settings", service_id=current_service.id))

    return render_template(
        "views/service-settings/branding/new/email-branding-enter-government-identity-logo-text.html",
        form=form,
        back_link=url_for(
            ".email_branding_request_government_identity_logo",
            service_id=service_id,
            **_email_branding_flow_query_params(request),
        ),
        error_summary_enabled=True,
    )


@main.route("/services/<uuid:service_id>/service-settings/email-branding/choose-logo", methods=["GET", "POST"])
@user_has_permissions("manage_service")
@service_belongs_to_org_type("central")
def email_branding_choose_logo(service_id):
    form = EmailBrandingChooseLogoForm()
    branding_choice = request.args.get("branding_choice")
    form.branding_options.data = form.branding_options.data or request.args.get("logo_type")

    if form.validate_on_submit():
        if form.branding_options.data == "org":
            if branding_choice == "govuk_and_org":
                return redirect(
                    url_for(
                        ".email_branding_upload_logo",
                        service_id=current_service.id,
                        back_link=".email_branding_choose_logo",
                        **_email_branding_flow_query_params(request, brand_type="both", logo_type="org"),
                    )
                )

            return redirect(
                url_for(
                    ".email_branding_choose_banner_type",
                    service_id=current_service.id,
                    back_link=".email_branding_choose_logo",
                    **_email_branding_flow_query_params(request, logo_type="org"),
                )
            )
        elif form.branding_options.data == "single_identity":
            return redirect(
                url_for(
                    ".email_branding_request_government_identity_logo",
                    service_id=current_service.id,
                    **_email_branding_flow_query_params(request, logo_type="single_identity"),
                )
            )

    return (
        render_template(
            "views/service-settings/branding/new/email-branding-choose-logo.html",
            form=form,
            branding_choice=branding_choice,
            error_summary_enabled=True,
            back_link=url_for(
                "main.email_branding_options",
                service_id=current_service.id,
                **_email_branding_flow_query_params(request, logo_type=None),
            ),
        ),
        400 if form.errors else 200,
    )


@main.route("/services/<uuid:service_id>/service-settings/email-branding/upload-logo", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def email_branding_upload_logo(service_id):
    form = EmailBrandingLogoUpload()

    if form.validate_on_submit():
        temporary_logo_key = logo_client.save_temporary_logo(form.logo.data, logo_type="email")

        return redirect(
            url_for(
                "main.email_branding_set_alt_text",
                service_id=service_id,
                **_email_branding_flow_query_params(request, logo=temporary_logo_key),
            )
        )

    abandon_flow_link = url_for(
        "main.email_branding_request",
        service_id=current_service.id,
        back_link=".email_branding_upload_logo",
        **_email_branding_flow_query_params(request),
    )
    if request.args.get("brand_type") == "org_banner":
        back_link = url_for(
            ".email_branding_choose_banner_colour",
            service_id=service_id,
            **_email_branding_flow_query_params(request, colour=None),
        )
    elif request.args.get("brand_type") == "both":
        back_link = url_for(
            ".email_branding_choose_logo",
            service_id=service_id,
            **_email_branding_flow_query_params(request),
        )
    else:
        back_link = url_for(
            ".email_branding_choose_banner_type",
            service_id=service_id,
            **_email_branding_flow_query_params(request),
        )

    return (
        render_template(
            "views/service-settings/branding/new/email-branding-upload-logo.html",
            form=form,
            back_link=back_link,
            abandon_flow_link=abandon_flow_link,
            error_summary_enabled=True,
        ),
        400 if form.errors else 200,
    )


def _should_set_default_org_email_branding(branding_choice):
    # 1. the user has chosen ‘[organisation name]’ in the first page of the journey
    user_chose_org_name = branding_choice == "organisation"
    # 2. and the organisation doesn’t have default branding already
    org_doesnt_have_default_branding = current_service.organisation.email_branding_id is None
    # 3. and the organisation is not central government
    #    (it might be appropriate for them to keep GOV.UK as a default instead)
    org_not_central = current_service.organisation_type != Organisation.TYPE_CENTRAL
    # 4. and the organisation has no other live services
    no_other_live_services_in_org = not any(
        service.id != current_service.id for service in current_service.organisation.live_services
    )

    return (
        user_chose_org_name and org_doesnt_have_default_branding and org_not_central and no_other_live_services_in_org
    )


@main.route("/services/<uuid:service_id>/service-settings/email-branding/preview", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def email_branding_set_alt_text(service_id):
    email_branding_data = _email_branding_flow_query_params(request)

    if not email_branding_data["brand_type"]:
        return redirect(url_for("main.email_branding_choose_banner_type", service_id=service_id))
    elif not email_branding_data["logo"]:
        return redirect(url_for("main.email_branding_upload_logo", service_id=service_id, **email_branding_data))

    form = EmailBrandingAltTextForm()

    if form.validate_on_submit():
        # we use these keys to keep track of user choices through the journey but we don't use them to save the branding
        branding_choice = email_branding_data.pop("branding_choice")
        email_branding_data.pop("logo_type", None)

        # Copy the temporary logo to its permanent location in S3 and overwrite the temporary logo key in the
        # email data to use in creating the logo in the DB.
        email_branding_data["logo"] = logo_client.save_permanent_logo(
            email_branding_data["logo"], logo_type="email", logo_key_extra=form.alt_text.data
        )

        new_email_branding = EmailBranding.create(
            alt_text=form.alt_text.data,
            **email_branding_data,
        )

        # set as service branding
        current_service.update(email_branding=new_email_branding.id)

        if current_service.organisation:
            # add to org pool
            organisations_client.add_brandings_to_email_branding_pool(
                current_service.organisation.id, [new_email_branding.id]
            )

            if _should_set_default_org_email_branding(branding_choice):
                current_service.organisation.update(email_branding_id=new_email_branding.id, delete_services_cache=True)

        flash(
            "You’ve changed your email branding. Send yourself an email to make sure it looks OK.", "default_with_tick"
        )

        return redirect(url_for("main.service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/branding/new/email-branding-set-alt-text.html",
        back_link=url_for(
            ".email_branding_upload_logo",
            service_id=service_id,
            **_email_branding_flow_query_params(request, logo=None),
        ),
        email_preview_data=email_branding_data,
        form=form,
        error_summary_enabled=True,
    )


def _email_branding_flow_query_params(request, **kwargs):
    """Return a dictionary containing values for the email branding flow.

    In order to create a new email branding for a user we need to collect and remember a series of information:
    - what kind of brand they want
    - what colour banner they want (optional)
    - what logo to use

    We pass this information between pages uses request query params. This function will collect them all from the
    URL, and optionally allows the caller to update or remove some of the options.

    To set a new value:
        _email_branding_flow_query_params(request, brand_type='org')

    To remove a value:
        _email_branding_flow_query_params(request, brand_type=None)

    These values can get passed to the `/_email` endpoint to generate a preview of a new brand.
    """
    return {
        k: kwargs.get(k, request.args.get(k)) for k in ("brand_type", "branding_choice", "colour", "logo", "logo_type")
    }


@main.route("/services/<uuid:service_id>/service-settings/email-branding/add-banner", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def email_branding_choose_banner_type(service_id):
    form = EmailBrandingChooseBanner()
    form.banner.data = form.banner.data or request.args.get("brand_type")

    if form.validate_on_submit():
        if form.banner.data == "org":
            return redirect(
                url_for(
                    ".email_branding_upload_logo",
                    service_id=service_id,
                    **_email_branding_flow_query_params(request, brand_type=form.banner.data),
                )
            )

        elif form.banner.data == "org_banner":
            return redirect(
                url_for(
                    ".email_branding_choose_banner_colour",
                    service_id=service_id,
                    **_email_branding_flow_query_params(request, brand_type=form.banner.data),
                )
            )

    org_type = current_service.organisation_type

    if any(get_email_branding_choices(current_service)):
        back_view_fallback = ".email_branding_choose_logo" if org_type == "central" else ".email_branding_options"
        back_view = request.args.get("back_link", back_view_fallback)
    else:
        back_view = ".email_branding_options"

    return (
        render_template(
            "views/service-settings/branding/new/email-branding-choose-banner.html",
            form=form,
            back_link=url_for(
                back_view,
                service_id=current_service.id,
                **_email_branding_flow_query_params(request, brand_type=None),
            ),
            error_summary_enabled=True,
        ),
        400 if form.errors else 200,
    )


@main.route("/services/<uuid:service_id>/service-settings/email-branding/choose-banner-colour", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def email_branding_choose_banner_colour(service_id):
    form = EmailBrandingChooseBannerColour()

    if form.validate_on_submit():
        return redirect(
            url_for(
                ".email_branding_upload_logo",
                service_id=service_id,
                **_email_branding_flow_query_params(request, colour=form.hex_colour.data),
            )
        )

    abandon_flow_link = url_for(
        ".email_branding_request",
        service_id=current_service.id,
        back_link=".email_branding_choose_banner_colour",
        **_email_branding_flow_query_params(request),
    )
    return (
        render_template(
            "views/service-settings/branding/new/email-branding-choose-banner-colour.html",
            form=form,
            back_link=url_for(
                ".email_branding_choose_banner_type",
                service_id=service_id,
                **_email_branding_flow_query_params(request),
            ),
            abandon_flow_link=abandon_flow_link,
            error_summary_enabled=True,
        ),
        400 if form.errors else 200,
    )


# ================= BRANDING - SHARED ==================


@main.route(
    "/services/<uuid:service_id>/service-settings/<branding_type:branding_type>-branding/confirm-change",
    methods=["GET", "POST"],
)
@user_has_permissions("manage_service")
def branding_option_preview(service_id, branding_type):
    if branding_type == "email":
        branding_pool = current_service.email_branding_pool
        back_link_query_params = _email_branding_flow_query_params(request)
    else:
        branding_pool = current_service.letter_branding_pool
        back_link_query_params = _letter_branding_flow_query_params(request)
    try:
        chosen_branding = branding_pool.get_item_by_id(request.args.get("branding_choice"))
    except branding_pool.NotFound:
        flash("No branding found for this id.")
        return redirect(url_for(f".{branding_type}_branding_options", service_id=current_service.id))

    if request.method == "POST":
        current_service.update(**{f"{branding_type}_branding": chosen_branding.id})

        flash(f"You’ve updated your {branding_type} branding", "default")
        return redirect(url_for(".service_settings", service_id=current_service.id))

    return render_template(
        "views/service-settings/branding/branding-option-preview.html",
        back_link_url=url_for(
            f".{branding_type}_branding_options", service_id=current_service.id, **back_link_query_params
        ),
        branding_type=branding_type,
        chosen_branding=chosen_branding,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/<branding_type:branding_type>-branding/nhs", methods=["GET", "POST"]
)
@user_has_permissions("manage_service")
def branding_nhs(service_id, branding_type):
    if branding_type == "email":
        branding = EmailBranding.NHS_ID
        back_link_query_params = _email_branding_flow_query_params(request)
    else:
        branding = LetterBranding.NHS_ID
        back_link_query_params = _letter_branding_flow_query_params(request)

    check_branding_allowed_for_service(branding, branding_type=branding_type)

    if request.method == "POST":
        current_service.update(**{f"{branding_type}_branding": branding})

        flash(f"You’ve updated your {branding_type} branding", "default")
        return redirect(url_for(".service_settings", service_id=current_service.id))

    return render_template(
        "views/service-settings/branding/branding-nhs.html",
        back_link_url=url_for(
            f".{branding_type}_branding_options",
            service_id=current_service.id,
            **back_link_query_params,
        ),
        branding_type=branding_type,
        nhs_branding_id=branding,
    )


# ================= LETTER BRANDING ===================


def _letter_branding_flow_query_params(request, **kwargs):
    """Return a dictionary containing values for the letter branding flow.

    We've got a variety of query parameters we want to pass around between pages. Any params that are passed in, we
    should pass through to ensure that back links continue to work the whole way through etc. In addition, we use the
    branding_choice param (from the letter_branding_options page) later on so need to pass that through.

    To set a new value:
        _letter_branding_flow_query_params(request, branding_choice='organisation')

    To remove a value:
        _letter_branding_flow_query_params(request, branding_choice=None)
    """
    return {k: kwargs.get(k, request.args.get(k)) for k in ("from_template", "branding_choice", "temp_filename")}


@main.route("/services/<uuid:service_id>/service-settings/letter-branding", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def letter_branding_options(service_id):
    form = ChooseLetterBrandingForm(current_service)
    form.options.data = form.options.data or request.args.get("branding_choice")
    from_template = request.args.get("from_template")

    if form.validate_on_submit():
        branding_choice = form.options.data

        if branding_choice == LetterBranding.NHS_ID:
            return redirect(
                url_for(
                    ".branding_nhs",
                    service_id=current_service.id,
                    branding_type="letter",
                    branding_choice=branding_choice,
                )
            )

        elif branding_choice in current_service.letter_branding_pool.ids:
            return redirect(
                url_for(
                    ".branding_option_preview",
                    service_id=current_service.id,
                    branding_choice=branding_choice,
                    branding_type="letter",
                )
            )
        else:
            return redirect(
                url_for(
                    ".letter_branding_upload_branding",
                    service_id=current_service.id,
                    **_letter_branding_flow_query_params(request, branding_choice=branding_choice),
                )
            )

    return render_template(
        "views/service-settings/branding/letter-branding-options.html",
        form=form,
        from_template=from_template,
        error_summary_enabled=True,
    )


@main.route("/services/<uuid:service_id>/service-settings/letter-branding/request", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def letter_branding_request(service_id):
    form = BrandingRequestForm()
    from_template = _letter_branding_flow_query_params(request)["from_template"]

    if form.validate_on_submit():
        ticket_message = render_template(
            "support-tickets/branding-request.txt",
            current_branding=current_service.letter_branding.name or "no",
            detail=form.branding_request.data,
        )
        ticket = NotifySupportTicket(
            subject=f"Letter branding request - {current_service.name}",
            message=ticket_message,
            ticket_type=NotifySupportTicket.TYPE_TASK,
            notify_ticket_type=NotifyTicketType.NON_TECHNICAL,
            user_name=current_user.name,
            user_email=current_user.email_address,
            org_id=current_service.organisation_id,
            org_type=current_service.organisation_type,
            service_id=current_service.id,
            notify_task_type="notify_task_letter_branding",
            user_created_at=current_user.created_at,
        )
        zendesk_client.send_ticket_to_zendesk(ticket)
        flash((THANKS_FOR_BRANDING_REQUEST_MESSAGE), "default")

        return redirect(
            url_for("main.view_template", service_id=current_service.id, template_id=from_template)
            if from_template
            else url_for(".service_settings", service_id=current_service.id)
        )

    return render_template(
        "views/service-settings/branding/branding-request.html",
        form=form,
        from_template=from_template,
        back_link=url_for(
            ".letter_branding_upload_branding",
            service_id=current_service.id,
            **_letter_branding_flow_query_params(request),
        ),
        error_summary_enabled=True,
    )


@main.route("/services/<uuid:service_id>/service-settings/letter-branding/upload-branding", methods=["GET", "POST"])
@user_has_permissions("manage_service")
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
                **_letter_branding_flow_query_params(request, temp_filename=temporary_logo_key),
            )
        )

    return render_template(
        "views/service-settings/branding/new/letter-branding-upload-branding.html",
        form=form,
        branding_choice=request.args.get("branding_choice"),
        back_link=url_for(
            ".letter_branding_options",
            service_id=current_service.id,
            **_letter_branding_flow_query_params(request),
        ),
        # TODO: Create branding-specific zendesk flow that creates branding ticket (see .letter_branding_request)
        abandon_flow_link=url_for(
            ".letter_branding_request", service_id=current_service.id, **_letter_branding_flow_query_params(request)
        ),
        error_summary_enabled=True,
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
@user_has_permissions("manage_service")
def letter_branding_set_name(service_id):
    letter_branding_data = _letter_branding_flow_query_params(request)
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

        if current_service.organisation:
            # add to org pool
            organisations_client.add_brandings_to_letter_branding_pool(
                current_service.organisation.id, [new_letter_branding.id]
            )

            if _should_set_default_org_letter_branding(letter_branding_data["branding_choice"]):
                current_service.organisation.update(
                    letter_branding_id=new_letter_branding.id,
                    delete_services_cache=True,
                )

        flash("You’ve changed your letter branding.", "default_with_tick")

        return redirect(url_for("main.service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/branding/new/letter-branding-set-name.html",
        back_link=url_for(
            ".letter_branding_upload_branding",
            service_id=service_id,
            **_letter_branding_flow_query_params(request, temp_filename=None),
        ),
        temp_filename=letter_filename_for_db_from_logo_key(temporary_logo_key),
        form=form,
        error_summary_enabled=True,
    )

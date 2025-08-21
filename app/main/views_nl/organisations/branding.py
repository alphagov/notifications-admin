from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from markupsafe import Markup
from werkzeug import Response

from app import current_organisation, organisations_client
from app.main import main
from app.main.forms import (
    AddEmailBrandingOptionsForm,
    AddLetterBrandingOptionsForm,
    AdminChangeOrganisationDefaultEmailBrandingForm,
    AdminChangeOrganisationDefaultLetterBrandingForm,
    SearchByNameForm,
)
from app.models.branding import AllEmailBranding, AllLetterBranding
from app.models.organisation import Organisation
from app.utils.user import user_is_platform_admin


def _handle_remove_email_branding(remove_branding_id) -> Response | None:
    """
    The user has clicked 'remove' on a brand and is either going to see a confirmation flash message
    or has clicked to confirm that flash message.
    """
    try:
        remove_branding = current_organisation.email_branding_pool.get_item_by_id(remove_branding_id)
    except current_organisation.email_branding_pool.NotFound:
        abort(400, f"Invalid email branding ID {remove_branding_id} for {current_organisation}")

    if request.method == "POST":
        organisations_client.remove_email_branding_from_pool(current_organisation.id, remove_branding_id)
        confirmation_message = f"Email branding ‘{remove_branding.name}’ removed."
        flash(confirmation_message, "default_with_tick")
        return redirect(url_for("main.organisation_email_branding", org_id=current_organisation.id))

    else:
        confirmation_question = Markup(
            render_template(
                "partials/flash_messages/branding_confirm_remove_brand.html",
                branding_name=remove_branding.name,
            )
        )

        flash(
            confirmation_question,
            "remove",
        )

    return None


def _handle_change_default_email_branding_to_govuk(is_central_government) -> Response | None:
    """
    This handles changing a central government organisation from a custom brand back to the default GOV.UK brand.
    If we're in here, then the user has either clicked the 'Reset to GOV.UK' link or they're clicking the
    button in the confirmation dialog.
    """
    # Only central government departments can have their brand reset to default GOV.UK
    if not is_central_government:
        return None

    if request.method == "POST":
        current_organisation.update(email_branding_id=None)
        return redirect(url_for("main.organisation_email_branding", org_id=current_organisation.id))

    else:
        current_brand = current_organisation.email_branding.name
        confirmation_question = Markup(
            render_template(
                "partials/flash_messages/email_branding_confirm_change_default_to_govuk.html",
                organisation_name=current_organisation.name,
                current_brand=current_brand,
            )
        )
        flash(confirmation_question, "make this email branding the default")

    return None


def _handle_change_default_email_branding(form, new_default_branding_id) -> Response | None:
    """
    Handle any change of branding to a non-default (GOV.UK) brand. This includes going from GOV.UK to a custom
    brand, and going from a custom brand to another custom brand. When moving from GOV.UK to a custom brand,
    there is a confirmation dialog step. When moving from a custom brand to another custom brand, it happens
    without any further confirmation.
    """

    def __get_email_branding_name(branding_id):
        try:
            return current_organisation.email_branding_pool.get_item_by_id(branding_id).name
        except current_organisation.email_branding_pool.NotFound:
            current_app.logger.info(
                "Email branding ID %(branding_id)s is not present in organisation %(org_name)s's email branding pool.",
                {"branding_id": branding_id, "org_name": current_organisation.name},
            )
            abort(400)

    # This block handles the case where an organisation is changing from GOV.UK to another explicit brand. We handle
    # this as a confirmation dialog + POST in order to explain to platform admins making this change that other services
    # on the GOV.UK default brand will be affected.
    if new_default_branding_id:
        # This also validates that the chosen brand is valid for the organisation.
        email_branding_name = __get_email_branding_name(new_default_branding_id)

        if request.method == "POST":
            current_organisation.update(delete_services_cache=True, email_branding_id=new_default_branding_id)
            return redirect(url_for("main.organisation_email_branding", org_id=current_organisation.id))

        confirmation_question = Markup(
            render_template(
                "partials/flash_messages/email_branding_confirm_change_brand_from_govuk.html",
                organisation_name=current_organisation.name,
                branding_name=email_branding_name,
            )
        )
        flash(
            confirmation_question,
            "make this email branding the default",
        )

    # This form submission handles users pressing `Make default` on a brand. We handle two cases here:
    # 1) If the org is currently on GOV.UK, we redirect them to the confirmation message explaining what happens when
    #    changing from GOV.UK to an explicit brand. This is handled by the block above.
    # 2) If the org is currently on an explicit brand and is changing to another, we just handle that change immediately
    #    and don't require confirmation.
    if form.validate_on_submit():
        if current_organisation.email_branding_id is None:
            return redirect(
                url_for(
                    "main.organisation_email_branding",
                    org_id=current_organisation.id,
                    new_default_branding_id=form.email_branding_id.data,
                )
            )

        current_organisation.update(email_branding_id=form.email_branding_id.data)
        return redirect(url_for("main.organisation_email_branding", org_id=current_organisation.id))

    return None


@main.route("/organisations/<uuid:org_id>/settings/email-branding", methods=["GET", "POST"])
@user_is_platform_admin
def organisation_email_branding(org_id):
    is_central_government = current_organisation.organisation_type == Organisation.TYPE_CENTRAL
    remove_branding_id = request.args.get("remove_branding_id")
    change_default_branding_to_govuk = "change_default_branding_to_govuk" in request.args
    new_default_branding_id = request.args.get("new_default_branding_id")
    form = AdminChangeOrganisationDefaultEmailBrandingForm()

    if remove_branding_id:
        if response := _handle_remove_email_branding(remove_branding_id):
            return response

    elif change_default_branding_to_govuk:
        if response := _handle_change_default_email_branding_to_govuk(is_central_government):
            return response

    elif response := _handle_change_default_email_branding(form, new_default_branding_id):
        return response

    # We only show this link to central government organisations.
    show_use_govuk_as_default_link = is_central_government and current_organisation.email_branding_id is not None

    return render_template(
        "views/organisations/organisation/settings/email-branding-options.html",
        form=form,
        show_use_govuk_as_default_link=show_use_govuk_as_default_link,
    )


@main.route("/organisations/<uuid:org_id>/settings/email-branding/add", methods=["GET", "POST"])
@user_is_platform_admin
def add_organisation_email_branding_options(org_id):
    form = AddEmailBrandingOptionsForm()

    form.branding_field.choices = [
        (branding.id, branding.name)
        for branding in sorted(AllEmailBranding().excluding(*current_organisation.email_branding_pool.ids))
    ]

    if form.validate_on_submit():
        selected_email_branding_ids = form.branding_field.data

        organisations_client.add_brandings_to_email_branding_pool(org_id, selected_email_branding_ids)

        if len(selected_email_branding_ids) == 1:
            msg = "1 email branding option added"
        else:
            msg = f"{len(selected_email_branding_ids)} email branding options added"

        flash(msg, "default_with_tick")
        return redirect(url_for(".organisation_email_branding", org_id=org_id))

    return render_template(
        "views/organisations/organisation/settings/add-email-branding-options.html",
        form=form,
        _search_form=SearchByNameForm(),
        error_summary_enabled=True,
    )


def _handle_remove_letter_branding(remove_branding_id):
    """
    The user has clicked 'remove' on a brand and is either going to see a confirmation flash message
    or has clicked to confirm that flash message.
    """

    try:
        remove_branding = current_organisation.letter_branding_pool.get_item_by_id(remove_branding_id)
    except current_organisation.letter_branding_pool.NotFound:
        abort(400, f"Invalid letter branding ID {remove_branding_id} for {current_organisation}")

    if request.method == "POST":
        organisations_client.remove_letter_branding_from_pool(current_organisation.id, remove_branding_id)
        flash(f"Letter branding ‘{remove_branding.name}’ removed.", "default_with_tick")
        return redirect(url_for("main.organisation_letter_branding", org_id=current_organisation.id))
    else:
        flash(
            Markup(
                render_template(
                    "partials/flash_messages/branding_confirm_remove_brand.html",
                    branding_name=remove_branding.name,
                )
            ),
            "remove",
        )


def _handle_change_default_letter_branding_to_none():
    """
    This handles settings an organisation's default letter branding to None.
    If we're in here, then the user has either clicked the 'Use no branding as default instead' link
    or they're clicking the button in the confirmation dialog.
    """
    if request.method == "POST":
        current_organisation.update(letter_branding_id=None)
        return redirect(url_for("main.organisation_letter_branding", org_id=current_organisation.id))

    else:
        flash(
            Markup(
                render_template(
                    "partials/flash_messages/letter_branding_confirm_change_default_to_none.html",
                )
            ),
            "remove default letter branding",
        )


def _handle_change_default_letter_branding(form, new_default_branding_id):
    """
    Handle any change of branding to a real brand (all cases except for making the default no branding).
    This includes going from no branding to a custom brand, and going from a custom brand to another custom brand.
    When moving from no branding to a custom brand, there is a confirmation dialog step. When moving from a custom
    brand to another custom brand, it happens without any further confirmation.
    """

    def __get_letter_branding_name(branding_id):
        try:
            return current_organisation.letter_branding_pool.get_item_by_id(branding_id).name
        except current_organisation.letter_branding_pool.NotFound:
            current_app.logger.info(
                "Letter branding ID %(id)s is not present in organisation %(org_name)s's letter branding pool.",
                {"id": branding_id, "org_name": current_organisation.name},
            )
            abort(400)

    # This block handles the case where an organisation is changing from no branding to an explicit brand. We handle
    # this as a confirmation dialog + POST in order to explain to platform admins making this change that other services
    # without branding will be affected.
    if new_default_branding_id:
        # This also validates that the chosen brand is valid for the organisation.
        letter_branding_name = __get_letter_branding_name(new_default_branding_id)

        if request.method == "POST":
            current_organisation.update(delete_services_cache=True, letter_branding_id=new_default_branding_id)
            return redirect(url_for("main.organisation_letter_branding", org_id=current_organisation.id))

        confirmation_question = Markup(
            render_template(
                "partials/flash_messages/letter_branding_confirm_change_brand_from_none.html",
                branding_name=letter_branding_name,
            )
        )
        flash(
            confirmation_question,
            "make this letter branding the default",
        )

    # This form submission handles users pressing `Make default` on a brand. We handle two cases here:
    # 1) If the org currently has no branding, we redirect them to the confirmation message explaining what happens when
    #    changing from no branding to an explicit brand. This is handled by the block above.
    # 2) If the org is currently on an explicit brand and is changing to another, we just handle that change immediately
    #    and don't require confirmation.
    if form.validate_on_submit():
        if current_organisation.letter_branding_id is None:
            return redirect(
                url_for(
                    "main.organisation_letter_branding",
                    org_id=current_organisation.id,
                    new_default_branding_id=form.letter_branding_id.data,
                )
            )

        current_organisation.update(letter_branding_id=form.letter_branding_id.data)
        return redirect(url_for("main.organisation_letter_branding", org_id=current_organisation.id))


@main.route("/organisations/<uuid:org_id>/settings/letter-branding", methods=["GET", "POST"])
@user_is_platform_admin
def organisation_letter_branding(org_id):
    remove_branding_id = request.args.get("remove_branding_id")
    change_default_branding_to_none = "change_default_branding_to_none" in request.args
    new_default_branding_id = request.args.get("new_default_branding_id")
    form = AdminChangeOrganisationDefaultLetterBrandingForm()

    if remove_branding_id:
        if response := _handle_remove_letter_branding(remove_branding_id):
            return response

    elif change_default_branding_to_none:
        if response := _handle_change_default_letter_branding_to_none():
            return response

    elif response := _handle_change_default_letter_branding(form, new_default_branding_id):
        return response

    return render_template(
        "views/organisations/organisation/settings/letter-branding-options.html",
        form=form,
    )


@main.route("/organisations/<uuid:org_id>/settings/letter-branding/add", methods=["GET", "POST"])
@user_is_platform_admin
def add_organisation_letter_branding_options(org_id):
    form = AddLetterBrandingOptionsForm()

    form.branding_field.choices = [
        (branding.id, branding.name)
        for branding in sorted(AllLetterBranding().excluding(*current_organisation.letter_branding_pool.ids))
    ]

    if form.validate_on_submit():
        selected_letter_branding_ids = form.branding_field.data

        organisations_client.add_brandings_to_letter_branding_pool(org_id, selected_letter_branding_ids)

        if len(selected_letter_branding_ids) == 1:
            msg = "1 letter branding option added"
        else:
            msg = f"{len(selected_letter_branding_ids)} letter branding options added"

        flash(msg, "default_with_tick")
        return redirect(url_for(".organisation_letter_branding", org_id=org_id))

    return render_template(
        "views/organisations/organisation/settings/add-letter-branding-options.html",
        form=form,
        _search_form=SearchByNameForm(),
        error_summary_enabled=True,
    )

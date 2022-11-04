from collections import OrderedDict
from datetime import datetime
from functools import partial
from typing import Optional

from flask import (
    Markup,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user
from notifications_python_client.errors import HTTPError
from werkzeug import Response
from werkzeug.exceptions import abort

from app import (
    current_organisation,
    current_service,
    org_invite_api_client,
    organisations_client,
)
from app.main import main
from app.main.forms import (
    AddEmailBrandingOptionsForm,
    AddGPOrganisationForm,
    AddLetterBrandingOptionsForm,
    AddNHSLocalOrganisationForm,
    AdminBillingDetailsForm,
    AdminChangeOrganisationDefaultEmailBrandingForm,
    AdminChangeOrganisationDefaultLetterBrandingForm,
    AdminNewOrganisationForm,
    AdminNotesForm,
    AdminOrganisationDomainsForm,
    AdminOrganisationGoLiveNotesForm,
    AdminPreviewBrandingForm,
    AdminSetLetterBrandingForm,
    InviteOrgUserForm,
    OrganisationAgreementSignedForm,
    OrganisationCrownStatusForm,
    OrganisationOrganisationTypeForm,
    RenameOrganisationForm,
    SearchByNameForm,
    SearchUsersForm,
)
from app.main.views.dashboard import (
    get_tuples_of_financial_years,
    requested_and_current_financial_year,
)
from app.models.branding import AllEmailBranding, AllLetterBranding
from app.models.organisation import AllOrganisations, Organisation
from app.models.user import InvitedOrgUser, User
from app.s3_client.s3_mou_client import get_mou
from app.utils.csv import Spreadsheet
from app.utils.user import user_has_permissions, user_is_platform_admin


@main.route("/organisations", methods=["GET"])
@user_is_platform_admin
def organisations():
    return render_template(
        "views/organisations/index.html",
        organisations=AllOrganisations(),
        search_form=SearchByNameForm(),
    )


@main.route("/organisations/add", methods=["GET", "POST"])
@user_is_platform_admin
def add_organisation():
    form = AdminNewOrganisationForm()

    if form.validate_on_submit():
        try:
            return redirect(
                url_for(
                    ".organisation_settings",
                    org_id=Organisation.create_from_form(form).id,
                )
            )
        except HTTPError as e:
            msg = "Organisation name already exists"
            if e.status_code == 400 and msg in e.message:
                form.name.errors.append("This organisation name is already in use")
            else:
                raise e

    return render_template("views/organisations/add-organisation.html", form=form)


@main.route("/services/<uuid:service_id>/add-gp-organisation", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def add_organisation_from_gp_service(service_id):
    if (not current_service.organisation_type == Organisation.TYPE_NHS_GP) or current_service.organisation:
        abort(403)

    form = AddGPOrganisationForm(service_name=current_service.name)

    if form.validate_on_submit():
        Organisation.create(
            form.get_organisation_name(),
            crown=False,
            organisation_type="nhs_gp",
            agreement_signed=False,
        ).associate_service(service_id)
        return redirect(
            url_for(
                ".service_agreement",
                service_id=service_id,
            )
        )

    return render_template("views/organisations/add-gp-organisation.html", form=form)


@main.route("/services/<uuid:service_id>/add-nhs-local-organisation", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def add_organisation_from_nhs_local_service(service_id):
    if (not current_service.organisation_type == Organisation.TYPE_NHS_LOCAL) or current_service.organisation:
        abort(403)

    form = AddNHSLocalOrganisationForm(
        organisation_choices=[
            (organisation.id, organisation.name)
            for organisation in sorted(AllOrganisations())
            if organisation.organisation_type == Organisation.TYPE_NHS_LOCAL
        ]
    )

    search_form = SearchByNameForm()

    if form.validate_on_submit():
        Organisation.from_id(form.organisations.data).associate_service(service_id)
        return redirect(
            url_for(
                ".service_agreement",
                service_id=service_id,
            )
        )

    return render_template(
        "views/organisations/add-nhs-local-organisation.html",
        form=form,
        search_form=search_form,
    )


@main.route("/organisations/<uuid:org_id>", methods=["GET"])
@user_has_permissions()
def organisation_dashboard(org_id):
    year, current_financial_year = requested_and_current_financial_year(request)
    services = current_organisation.services_and_usage(financial_year=year)["services"]
    return render_template(
        "views/organisations/organisation/index.html",
        services=services,
        years=get_tuples_of_financial_years(
            partial(url_for, ".organisation_dashboard", org_id=current_organisation.id),
            start=current_financial_year - 2,
            end=current_financial_year,
        ),
        selected_year=year,
        search_form=SearchByNameForm() if len(services) > 7 else None,
        **{
            f"total_{key}": sum(service[key] for service in services)
            for key in ("emails_sent", "sms_cost", "letter_cost")
        },
        download_link=url_for(".download_organisation_usage_report", org_id=org_id, selected_year=year),
    )


@main.route("/organisations/<uuid:org_id>/download-usage-report.csv", methods=["GET"])
@user_has_permissions()
def download_organisation_usage_report(org_id):
    selected_year = request.args.get("selected_year")
    services_usage = current_organisation.services_and_usage(financial_year=selected_year)["services"]

    unit_column_names = OrderedDict(
        [
            ("service_id", "Service ID"),
            ("service_name", "Service Name"),
            ("emails_sent", "Emails sent"),
            ("sms_remainder", "Free text message allowance remaining"),
        ]
    )

    monetary_column_names = OrderedDict(
        [("sms_cost", "Spent on text messages (£)"), ("letter_cost", "Spent on letters (£)")]
    )

    org_usage_data = [list(unit_column_names.values()) + list(monetary_column_names.values())] + [
        [service[attribute] for attribute in unit_column_names.keys()]
        + ["{:,.2f}".format(service[attribute]) for attribute in monetary_column_names.keys()]
        for service in services_usage
    ]

    return (
        Spreadsheet.from_rows(org_usage_data).as_csv_data,
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": (
                "inline;"
                'filename="{} organisation usage report for year {}'
                ' - generated on {}.csv"'.format(
                    current_organisation.name, selected_year, datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                )
            ),
        },
    )


@main.route("/organisations/<uuid:org_id>/trial-services", methods=["GET"])
@user_is_platform_admin
def organisation_trial_mode_services(org_id):
    return render_template(
        "views/organisations/organisation/trial-mode-services.html",
        search_form=SearchByNameForm(),
    )


@main.route("/organisations/<uuid:org_id>/users", methods=["GET"])
@user_has_permissions()
def manage_org_users(org_id):
    return render_template(
        "views/organisations/organisation/users/index.html",
        users=current_organisation.team_members,
        show_search_box=(len(current_organisation.team_members) > 7),
        form=SearchUsersForm(),
    )


@main.route("/organisations/<uuid:org_id>/users/invite", methods=["GET", "POST"])
@user_has_permissions()
def invite_org_user(org_id):
    form = InviteOrgUserForm(inviter_email_address=current_user.email_address)
    if form.validate_on_submit():
        email_address = form.email_address.data
        invited_org_user = InvitedOrgUser.create(current_user.id, org_id, email_address)

        flash("Invite sent to {}".format(invited_org_user.email_address), "default_with_tick")
        return redirect(url_for(".manage_org_users", org_id=org_id))

    return render_template("views/organisations/organisation/users/invite-org-user.html", form=form)


@main.route("/organisations/<uuid:org_id>/users/<uuid:user_id>", methods=["GET"])
@user_has_permissions()
def edit_organisation_user(org_id, user_id):
    # The only action that can be done to an org user is to remove them from the org.
    # This endpoint is used to get the ID of the user to delete without passing it as a
    # query string, but it uses the template for all org team members in order to avoid
    # having a page containing a single link.
    return render_template(
        "views/organisations/organisation/users/index.html",
        users=current_organisation.team_members,
        show_search_box=(len(current_organisation.team_members) > 7),
        form=SearchUsersForm(),
        user_to_remove=User.from_id(user_id),
    )


@main.route("/organisations/<uuid:org_id>/users/<uuid:user_id>/delete", methods=["POST"])
@user_has_permissions()
def remove_user_from_organisation(org_id, user_id):
    organisations_client.remove_user_from_organisation(org_id, user_id)

    return redirect(url_for(".show_accounts_or_dashboard"))


@main.route("/organisations/<uuid:org_id>/cancel-invited-user/<uuid:invited_user_id>", methods=["GET"])
@user_has_permissions()
def cancel_invited_org_user(org_id, invited_user_id):
    org_invite_api_client.cancel_invited_user(org_id=org_id, invited_user_id=invited_user_id)

    invited_org_user = InvitedOrgUser.by_id_and_org_id(org_id, invited_user_id)

    flash(f"Invitation cancelled for {invited_org_user.email_address}", "default_with_tick")
    return redirect(url_for("main.manage_org_users", org_id=org_id))


@main.route("/organisations/<uuid:org_id>/settings/", methods=["GET"])
@user_is_platform_admin
def organisation_settings(org_id):
    return render_template("views/organisations/organisation/settings/index.html")


@main.route("/organisations/<uuid:org_id>/settings/edit-name", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_name(org_id):
    form = RenameOrganisationForm(name=current_organisation.name)

    if form.validate_on_submit():

        try:
            current_organisation.update(name=form.name.data)
        except HTTPError as http_error:
            error_msg = "Organisation name already exists"
            if http_error.status_code == 400 and error_msg in http_error.message:
                form.name.errors.append("This organisation name is already in use")
            else:
                raise http_error
        else:
            return redirect(url_for(".organisation_settings", org_id=org_id))

    return render_template(
        "views/organisations/organisation/settings/edit-name.html",
        form=form,
    )


@main.route("/organisations/<uuid:org_id>/settings/edit-type", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_type(org_id):

    form = OrganisationOrganisationTypeForm(organisation_type=current_organisation.organisation_type)

    if form.validate_on_submit():
        current_organisation.update(
            organisation_type=form.organisation_type.data,
            delete_services_cache=True,
        )
        return redirect(url_for(".organisation_settings", org_id=org_id))

    return render_template(
        "views/organisations/organisation/settings/edit-type.html",
        form=form,
    )


@main.route("/organisations/<uuid:org_id>/settings/edit-crown-status", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_crown_status(org_id):

    form = OrganisationCrownStatusForm(
        crown_status={
            True: "crown",
            False: "non-crown",
            None: "unknown",
        }.get(current_organisation.crown)
    )

    if form.validate_on_submit():
        organisations_client.update_organisation(
            current_organisation.id,
            crown={
                "crown": True,
                "non-crown": False,
                "unknown": None,
            }.get(form.crown_status.data),
        )
        return redirect(url_for(".organisation_settings", org_id=org_id))

    return render_template(
        "views/organisations/organisation/settings/edit-crown-status.html",
        form=form,
    )


@main.route("/organisations/<uuid:org_id>/settings/edit-agreement", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_agreement(org_id):

    form = OrganisationAgreementSignedForm(
        agreement_signed={
            True: "yes",
            False: "no",
            None: "unknown",
        }.get(current_organisation.agreement_signed)
    )

    if form.validate_on_submit():
        organisations_client.update_organisation(
            current_organisation.id,
            agreement_signed={
                "yes": True,
                "no": False,
                "unknown": None,
            }.get(form.agreement_signed.data),
        )
        return redirect(url_for(".organisation_settings", org_id=org_id))

    return render_template(
        "views/organisations/organisation/settings/edit-agreement.html",
        form=form,
    )


def _handle_remove_email_branding(remove_branding_id) -> Optional[Response]:
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


def _handle_change_default_email_branding_to_govuk(is_central_government) -> Optional[Response]:
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


def _handle_change_default_email_branding(form, new_default_branding_id) -> Optional[Response]:
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
                f"Email branding ID {branding_id} is not present in organisation {current_organisation.name}'s "
                f"email branding pool."
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
        search_form=SearchByNameForm(),
    )


@main.route("/organisations/<uuid:org_id>/settings/set-letter-branding", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_letter_branding(org_id):
    form = AdminSetLetterBrandingForm(
        all_branding_options=AllLetterBranding().as_id_and_name,
        current_branding=current_organisation.letter_branding_id,
    )

    if form.validate_on_submit():
        return redirect(
            url_for(
                ".organisation_preview_letter_branding",
                org_id=org_id,
                branding_style=form.branding_style.data,
            )
        )

    return render_template(
        "views/organisations/organisation/settings/set-letter-branding.html", form=form, search_form=SearchByNameForm()
    )


@main.route("/organisations/<uuid:org_id>/settings/preview-letter-branding", methods=["GET", "POST"])
@user_is_platform_admin
def organisation_preview_letter_branding(org_id):
    branding_style = request.args.get("branding_style")

    form = AdminPreviewBrandingForm(branding_style=branding_style)

    if form.validate_on_submit():
        current_organisation.update(
            letter_branding_id=form.branding_style.data,
            delete_services_cache=True,
        )
        return redirect(url_for(".organisation_settings", org_id=org_id))

    return render_template(
        "views/organisations/organisation/settings/preview-letter-branding.html",
        form=form,
        action=url_for("main.organisation_preview_letter_branding", org_id=org_id),
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
                f"Letter branding ID {branding_id} is not present in organisation {current_organisation.name}'s "
                "letter branding pool."
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
        search_form=SearchByNameForm(),
    )


@main.route("/organisations/<uuid:org_id>/settings/edit-organisation-domains", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_domains(org_id):

    form = AdminOrganisationDomainsForm()

    if form.validate_on_submit():
        try:
            organisations_client.update_organisation(
                org_id,
                domains=list(OrderedDict.fromkeys(domain.lower() for domain in filter(None, form.domains.data))),
            )
        except HTTPError as e:
            error_message = "Domain already exists"
            if e.status_code == 400 and error_message in e.message:
                flash("This domain is already in use", "error")
                return render_template(
                    "views/organisations/organisation/settings/edit-domains.html",
                    form=form,
                )
            else:
                raise e
        return redirect(url_for(".organisation_settings", org_id=org_id))

    if request.method == "GET":
        form.populate(current_organisation.domains)

    return render_template(
        "views/organisations/organisation/settings/edit-domains.html",
        form=form,
    )


@main.route("/organisations/<uuid:org_id>/settings/edit-go-live-notes", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_go_live_notes(org_id):

    form = AdminOrganisationGoLiveNotesForm()

    if form.validate_on_submit():
        organisations_client.update_organisation(org_id, request_to_go_live_notes=form.request_to_go_live_notes.data)
        return redirect(url_for(".organisation_settings", org_id=org_id))

    org = organisations_client.get_organisation(org_id)
    form.request_to_go_live_notes.data = org["request_to_go_live_notes"]

    return render_template(
        "views/organisations/organisation/settings/edit-go-live-notes.html",
        form=form,
    )


@main.route("/organisations/<uuid:org_id>/settings/notes", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_notes(org_id):
    form = AdminNotesForm(notes=current_organisation.notes)

    if form.validate_on_submit():

        if form.notes.data == current_organisation.notes:
            return redirect(url_for(".organisation_settings", org_id=org_id))

        current_organisation.update(notes=form.notes.data)
        return redirect(url_for(".organisation_settings", org_id=org_id))

    return render_template(
        "views/organisations/organisation/settings/edit-organisation-notes.html",
        form=form,
    )


@main.route("/organisations/<uuid:org_id>/settings/edit-billing-details", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_billing_details(org_id):
    form = AdminBillingDetailsForm(
        billing_contact_email_addresses=current_organisation.billing_contact_email_addresses,
        billing_contact_names=current_organisation.billing_contact_names,
        billing_reference=current_organisation.billing_reference,
        purchase_order_number=current_organisation.purchase_order_number,
        notes=current_organisation.notes,
    )

    if form.validate_on_submit():
        current_organisation.update(
            billing_contact_email_addresses=form.billing_contact_email_addresses.data,
            billing_contact_names=form.billing_contact_names.data,
            billing_reference=form.billing_reference.data,
            purchase_order_number=form.purchase_order_number.data,
            notes=form.notes.data,
        )
        return redirect(url_for(".organisation_settings", org_id=org_id))

    return render_template(
        "views/organisations/organisation/settings/edit-organisation-billing-details.html",
        form=form,
    )


@main.route("/organisations/<uuid:org_id>/settings/archive", methods=["GET", "POST"])
@user_is_platform_admin
def archive_organisation(org_id):
    if not current_organisation.active:
        abort(403)

    if request.method == "POST":
        try:
            organisations_client.archive_organisation(org_id)
        except HTTPError as e:
            if e.status_code == 400 and ("team members" in e.message or "services" in e.message):
                flash(e.message)
                return organisation_settings(org_id)
            else:
                raise e

        flash(f"‘{current_organisation.name}’ was deleted", "default_with_tick")
        return redirect(url_for(".choose_account"))

    flash(
        f"Are you sure you want to delete ‘{current_organisation.name}’? There’s no way to undo this.",
        "delete",
    )
    return organisation_settings(org_id)


@main.route("/organisations/<uuid:org_id>/billing")
@user_is_platform_admin
def organisation_billing(org_id):
    return render_template("views/organisations/organisation/billing.html")


@main.route("/organisations/<uuid:org_id>/agreement.pdf")
@user_is_platform_admin
def organisation_download_agreement(org_id):
    return send_file(**get_mou(current_organisation.crown_status_or_404))

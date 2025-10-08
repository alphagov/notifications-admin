from datetime import datetime
from functools import partial

from flask import flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError
from werkzeug.exceptions import abort

from app import (
    current_organisation,
    current_service,
    org_invite_api_client,
    organisations_client,
)
from app.main import main
from app.main.forms import (
    AddGPOrganisationForm,
    AddNHSLocalOrganisationForm,
    AdminBillingDetailsForm,
    AdminNewOrganisationForm,
    AdminNotesForm,
    AdminOrganisationDomainsForm,
    AdminOrganisationGoLiveNotesForm,
    InviteOrgUserForm,
    OrganisationAgreementSignedForm,
    OrganisationCrownStatusForm,
    OrganisationOrganisationTypeForm,
    OrganisationUserPermissionsForm,
    RenameOrganisationForm,
    SearchByNameForm,
    SearchUsersForm,
    YesNoSettingForm,
)
from app.main.views.dashboard import (
    get_tuples_of_financial_years,
    requested_and_current_financial_year,
)
from app.models.organisation import AllOrganisations, Organisation
from app.models.user import InvitedOrgUser
from app.s3_client.s3_mou_client import get_mou
from app.utils.csv import Spreadsheet
from app.utils.user import user_has_permissions, user_is_platform_admin
from app.utils.user_permissions import organisation_user_permission_options


@main.route("/organisations", methods=["GET"])
@user_is_platform_admin
def organisations():
    return render_template(
        "views/organisations/index.html",
        organisations=AllOrganisations(),
        _search_form=SearchByNameForm(),
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
            org_name_exists_message = "Organisation name already exists"
            if e.status_code == 400 and org_name_exists_message in e.message:
                form.name.errors.append("This organisation name is already in use.")
            else:
                raise e

    return render_template("views/organisations/add-organisation.html", form=form, error_summary_enabled=True)


@main.route("/services/<uuid:service_id>/add-gp-organisation", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def add_organisation_from_gp_service(service_id):
    if (not current_service.organisation_type == Organisation.TYPE_NHS_GP) or current_service.organisation:
        abort(403)

    form = AddGPOrganisationForm(service_name=current_service.name)

    if form.validate_on_submit():
        try:
            Organisation.create(
                form.get_organisation_name(),
                crown=False,
                organisation_type="nhs_gp",
                agreement_signed=False,
            ).associate_service(service_id)
        except HTTPError as e:
            org_name_exists_message = "Organisation name already exists"
            if e.status_code == 400 and org_name_exists_message in e.message:
                flash("This organisation name is already in use.")
            else:
                raise e

        else:
            return redirect(url_for(".service_agreement", service_id=service_id))

    return render_template("views/organisations/add-gp-organisation.html", form=form, error_summary_enabled=True)


@main.route("/services/<uuid:service_id>/add-nhs-local-organisation", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def add_organisation_from_nhs_local_service(service_id):
    if (not current_service.organisation_type == Organisation.TYPE_NHS_LOCAL) or current_service.organisation:
        abort(403)

    form = AddNHSLocalOrganisationForm(
        organisation_choices=[
            (organisation.id, organisation.name)
            for organisation in sorted(AllOrganisations())
            if organisation.organisation_type == Organisation.TYPE_NHS_LOCAL and organisation.active
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
        _search_form=search_form,
    )


@main.route("/organisations/<uuid:org_id>", methods=["GET"])
@user_has_permissions()
def organisation_dashboard(org_id):
    year, current_financial_year = requested_and_current_financial_year(request)
    services, updated_at = current_organisation.services_and_usage(financial_year=year)
    return render_template(
        "views/organisations/organisation/index.html",
        services=services,
        years=get_tuples_of_financial_years(
            partial(url_for, ".organisation_dashboard", org_id=current_organisation.id),
            start=current_financial_year - 2,
            end=current_financial_year,
        ),
        selected_year=year,
        updated_at=updated_at,
        _search_form=SearchByNameForm() if len(services) > 7 else None,
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
    services_usage, _ = current_organisation.services_and_usage(financial_year=selected_year)

    unit_column_names = {
        "service_id": "Service ID",
        "service_name": "Service Name",
        "emails_sent": "Emails sent",
        "sms_remainder": "Free text message allowance remaining",
    }

    monetary_column_names = {
        "sms_cost": "Spent on text messages (£)",
        "letter_cost": "Spent on letters (£)",
    }

    org_usage_data = [list(unit_column_names.values()) + list(monetary_column_names.values())] + [
        [service[attribute] for attribute in unit_column_names.keys()]
        + [f"{service[attribute]:,.2f}" for attribute in monetary_column_names.keys()]
        for service in services_usage
    ]

    return (
        Spreadsheet.from_rows(org_usage_data).as_csv_data,
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": (
                'inline;filename="{} organisation usage report for year {} - generated on {}.csv"'.format(
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
        _search_form=SearchByNameForm(),
    )


@main.route("/organisations/<uuid:org_id>/users", methods=["GET"])
@user_has_permissions()
def manage_org_users(org_id):
    return render_template(
        "views/organisations/organisation/users/index.html",
        users=current_organisation.team_members,
        show_search_box=(len(current_organisation.team_members) > 7),
        form=SearchUsersForm(),
        permissions=organisation_user_permission_options,
    )


@main.route("/organisations/<uuid:org_id>/users/invite", methods=["GET", "POST"])
@user_has_permissions()
def invite_org_user(org_id):
    form = InviteOrgUserForm(inviter_email_address=current_user.email_address)

    if form.validate_on_submit():
        invited_org_user = InvitedOrgUser.create(
            invite_from_id=current_user.id,
            org_id=org_id,
            email_address=form.email_address.data,
            permissions=list(form.permissions),
        )

        flash(f"Invite sent to {invited_org_user.email_address}", "default_with_tick")
        return redirect(url_for(".manage_org_users", org_id=org_id))

    return render_template(
        "views/organisations/organisation/users/invite-org-user.html",
        form=form,
        error_summary_enabled=True,
    )


@main.route("/organisations/<uuid:org_id>/users/<uuid:user_id>", methods=["GET", "POST"])
@user_has_permissions()
def edit_organisation_user(org_id, user_id):
    user = current_organisation.get_team_member(user_id)
    if not user.is_editable_by(current_user):
        abort(403)

    form = OrganisationUserPermissionsForm.from_user_and_organisation(user, current_organisation)

    if form.validate_on_submit():
        user.set_organisation_permissions(
            org_id,
            permissions=list(form.permissions),
            set_by_id=current_user.id,
        )
        return redirect(url_for(".manage_org_users", org_id=org_id))

    return render_template(
        "views/organisations/organisation/users/edit-org-user-permissions.html",
        current_organisation=current_organisation,
        user=user,
        form=form,
        delete=request.args.get("delete"),
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
        "views/organisations/organisation/settings/edit-name.html", form=form, error_summary_enabled=True
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
        crown_data = {
            "crown": True,
            "non-crown": False,
            "unknown": None,
        }.get(form.crown_status.data)

        current_organisation.update(crown=crown_data, delete_services_cache=True)
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


@main.route("/organisations/<uuid:org_id>/settings/edit-organisation-domains", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_domains(org_id):
    form = AdminOrganisationDomainsForm()

    if form.validate_on_submit():
        try:
            organisations_client.update_organisation(
                org_id,
                domains=list(dict.fromkeys(domain.lower() for domain in form.domains.data if domain)),
            )
        except HTTPError as e:
            error_message = "Domain already exists"
            if e.status_code == 400 and error_message in e.message:
                flash("This domain is already in use", "error")
                return render_template(
                    "views/organisations/organisation/settings/edit-domains.html",
                    form=form,
                    error_summary_enabled=True,
                )
            else:
                raise e
        return redirect(url_for(".organisation_settings", org_id=org_id))

    if request.method == "GET":
        form.populate(current_organisation.domains)

    return render_template(
        "views/organisations/organisation/settings/edit-domains.html",
        form=form,
        error_summary_enabled=True,
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


@main.route("/organisations/<uuid:org_id>/settings/edit-can-approve-own-go-live-requests", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_can_approve_own_go_live_requests(org_id):
    form = YesNoSettingForm(
        name="Can this organisation approve its own go live requests?",
        enabled=current_organisation.can_approve_own_go_live_requests,
    )

    if form.validate_on_submit():
        current_organisation.update(can_approve_own_go_live_requests=form.enabled.data)
        return redirect(url_for(".organisation_settings", org_id=org_id))

    return render_template(
        "views/organisations/organisation/settings/edit-can-approve-own-go-live-requests.html",
        form=form,
    )


@main.route("/organisations/<uuid:org_id>/settings/edit-can-ask-to-join-a-service", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_can_ask_to_join_a_service(org_id):
    form = YesNoSettingForm(
        name="Can people ask to join services in this organisation?",
        enabled=current_organisation.can_ask_to_join_a_service,
    )
    permissions = current_organisation.permissions

    if form.enabled.data:
        if "can_ask_to_join_a_service" not in permissions:
            permissions.extend(["can_ask_to_join_a_service"])
    else:
        while "can_ask_to_join_a_service" in permissions:
            permissions.remove("can_ask_to_join_a_service")

    if form.validate_on_submit():
        current_organisation.update(permissions=permissions)
        return redirect(url_for(".organisation_settings", org_id=org_id))

    return render_template(
        "views/organisations/organisation/settings/edit-can-ask-to-join-a-service.html",
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
        return redirect(url_for(".your_services"))

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

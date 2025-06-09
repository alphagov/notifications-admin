from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import current_service, organisations_client
from app.main import main
from app.main.forms import OnOffSettingForm, ServiceGoLiveDecisionForm, UniqueServiceForm
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/make-service-live", methods=["GET"])
@user_has_permissions(allow_org_user=True)
def org_member_make_service_live_start(service_id):
    if current_service.live:
        return render_template("views/service-already-live.html", prompt_to_switch_service=False), 410

    if current_user.platform_admin and not current_service.organisation_id:
        return render_template("views/service-settings/service-no-organisation.html"), 410

    if not current_user.can_make_service_live(current_service):
        abort(403)

    return render_template(
        "views/organisations-admin/approve-service-start.html",
        organisation=current_service.organisation_id,
    )


@main.route("/services/<uuid:service_id>/make-service-live/unique-service", methods=["GET", "POST"])
@user_has_permissions(allow_org_user=True)
def org_member_make_service_live_check_unique(service_id):
    if current_service.live:
        return render_template("views/service-already-live.html", prompt_to_switch_service=False), 410

    if not current_user.can_make_service_live(current_service):
        abort(403)

    form = UniqueServiceForm(service_name=current_service.name)

    # Re-populate the form field data from URL query args, if present. This allows backlinks to take a user back to
    # this page and display the state the page was on when they submitted the form previously.
    if (unique := request.args.get("unique")) and unique in {"yes", "unsure", "no"} and request.method == "GET":
        form.is_unique.data = unique

    if form.validate_on_submit():
        unique = form.is_unique.data
        if unique == "no":
            return redirect(
                url_for(
                    ".org_member_make_service_live_decision",
                    service_id=current_service.id,
                    unique=unique,
                )
            )

        return redirect(
            url_for(".org_member_make_service_live_service_name", service_id=current_service.id, unique=unique)
        )

    return render_template(
        "views/organisations-admin/approve-service-check-unique.html",
        organisation=current_service.organisation_id,
        form=form,
        error_summary_enabled=True,
        back_link=url_for(
            ".org_member_make_service_live_start",
            service_id=current_service.id,
        ),
    )


@main.route("/services/<uuid:service_id>/make-service-live/service-name", methods=["GET", "POST"])
@user_has_permissions(allow_org_user=True)
def org_member_make_service_live_service_name(service_id):
    if current_service.live:
        return render_template("views/service-already-live.html", prompt_to_switch_service=False), 410

    if not current_user.can_make_service_live(current_service):
        abort(403)

    if "unique" not in request.args:
        return redirect(url_for(".org_member_make_service_live_start", service_id=current_service.id))
    elif (unique := request.args.get("unique").lower()) == "no":
        return redirect(url_for(".org_member_make_service_live_decision", service_id=current_service.id, unique=unique))

    form = OnOffSettingForm(
        truthy="Yes",
        falsey="No",
        name=f"Will recipients understand the name ‘{current_service.name}’?",
        choices_for_error_message="‘yes’ if recipients will understand the service name",
    )

    # Re-populate the form field data from URL query args, if present. This allows backlinks to take a user back to
    # this page and display the state the page was on when they submitted the form previously.
    if (name := request.args.get("name")) and name in {"ok", "bad"} and request.method == "GET":
        form.enabled.data = name == "ok"

    if form.validate_on_submit():
        redirect_kwargs = {"name": "ok" if form.enabled.data else "bad", "unique": unique}

        if form.enabled.data and unique == "yes":
            return redirect(
                url_for(".org_member_make_service_live_decision", service_id=current_service.id, **redirect_kwargs)
            )

        organisations_client.notify_org_member_about_next_steps_of_go_live_request(
            service_id=current_service.id,
            service_name=current_service.name,
            to=current_user.email_address,
            check_if_unique=unique == "unsure",
            unclear_service_name=form.enabled.data is False,
        )

        return redirect(
            url_for(".org_member_make_service_live_contact_user", service_id=current_service.id, **redirect_kwargs)
        )

    return render_template(
        "views/organisations-admin/approve-service-service-name.html",
        organisation=current_service.organisation,
        form=form,
        error_summary_enabled=True,
        back_link=url_for(
            ".org_member_make_service_live_check_unique",
            service_id=current_service.id,
            unique=request.args.get("unique"),
        ),
    )


@main.route("/services/<uuid:service_id>/make-service-live/contact-user", methods=["GET"])
@user_has_permissions(allow_org_user=True)
def org_member_make_service_live_contact_user(service_id):
    if current_service.live:
        return render_template("views/service-already-live.html", prompt_to_switch_service=False), 410

    if not current_user.can_make_service_live(current_service):
        abort(403)

    # Validate expected query params
    name = request.args.get("name", "").lower()
    unique = request.args.get("unique", "").lower()
    if "name" not in request.args or "unique" not in request.args:
        return redirect(url_for(".org_member_make_service_live_start", service_id=current_service.id))
    elif name not in {"ok", "bad"} or unique not in {"yes", "unsure", "no"}:
        abort(400)
    elif unique == "no" or (name == "ok" and unique == "yes"):
        return redirect(
            url_for(".org_member_make_service_live_decision", service_id=current_service.id, name=name, unique=unique)
        )

    return render_template(
        "views/organisations-admin/approve-service-contact-user.html",
        organisation=current_service.organisation_id,
        name=name,
        unique=unique,
        back_link=url_for(
            ".org_member_make_service_live_service_name",
            service_id=current_service.id,
            name=request.args.get("name"),
            unique=request.args.get("unique"),
        ),
    )


@main.route("/services/<uuid:service_id>/make-service-live/decision", methods=["GET", "POST"])
@user_has_permissions(allow_org_user=True)
def org_member_make_service_live_decision(service_id):
    if current_service.live:
        return render_template("views/service-already-live.html", prompt_to_switch_service=False), 410

    if not current_user.can_make_service_live(current_service):
        abort(403)

    if "unique" not in request.args:
        return redirect(url_for(".org_member_make_service_live_start", service_id=current_service.id))

    unique = request.args.get("unique").lower()
    cannot_approve = unique == "no"

    form = ServiceGoLiveDecisionForm(
        name="What would you like to do?",
        truthy="Approve the request and make this service live",
        falsey="Reject the request",
        choices_for_error_message="reject" if unique == "no" else "approve or reject",
    )
    if cannot_approve and form.enabled.data is True:
        form.enabled.data = None

    if form.validate_on_submit():
        if form.enabled.data:
            flash("This service is now live. We’ll email the team to let them know.", "default_with_tick")
        else:
            organisations_client.notify_service_member_of_rejected_go_live_request(
                service_id=service_id,
                service_member_name=current_service.go_live_user.name,
                service_name=current_service.name,
                organisation_name=current_service.organisation.name,
                rejection_reason=form.rejection_reason.data,
                organisation_team_member_name=current_user.name,
                organisation_team_member_email=current_user.email_address,
            )
            flash(
                (
                    "You rejected the request to go live for this service. "
                    f"We’ll email {current_service.go_live_user.name} to let them know."
                ),
                "default",
            )

        current_service.update_status(live=form.enabled.data)

        return redirect(url_for(".organisation_dashboard", org_id=current_service.organisation_id))

    back_link = (
        url_for(
            ".org_member_make_service_live_service_name",
            service_id=current_service.id,
            name=request.args.get("name"),
            unique=request.args.get("unique"),
        )
        if "name" in request.args
        else url_for(
            ".org_member_make_service_live_check_unique",
            service_id=current_service.id,
            unique=request.args.get("unique"),
        )
    )

    return render_template(
        "views/organisations-admin/approve-service-decision.html",
        form=form,
        cannot_approve=cannot_approve,
        error_summary_enabled=True,
        organisation=current_service.organisation_id,
        back_link=back_link,
    )

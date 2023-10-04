from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import current_service
from app.main import main
from app.main.forms import OnOffSettingForm, YesNoSettingForm
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/make-service-live", methods=["GET", "POST"])
@user_has_permissions(allow_org_user=True)
def make_service_live(service_id):
    if current_service.live:
        return render_template("views/service-settings/service-already-live.html", prompt_to_switch_service=False), 410

    if not current_user.can_make_service_live(current_service):
        abort(403)

    form = OnOffSettingForm(
        name="What would you like to do?",
        truthy="Approve the request and make this service live",
        falsey="Reject the request",
        choices_for_error_message="approve or reject",
    )

    if form.validate_on_submit():
        current_service.update_status(live=form.enabled.data)

        if form.enabled.data:
            flash(f"‘{current_service.name}’ is now live", "default_with_tick")
        else:
            flash("Request to go live rejected", "default")

        return redirect(url_for(".organisation_dashboard", org_id=current_service.organisation_id))

    return render_template(
        "views/make-service-live.html",
        form=form,
        title="Make service live",
        organisation=current_service.organisation_id,
    )


@main.route("/services/<uuid:service_id>/make-service-live/start", methods=["GET"])
@user_has_permissions(allow_org_user=True)
def org_member_make_service_live_start(service_id):
    if current_service.live:
        return render_template("views/service-settings/service-already-live.html", prompt_to_switch_service=False), 410

    if not current_user.can_make_service_live(current_service):
        abort(403)

    return render_template(
        "views/org-service-approver-start.html",
        organisation=current_service.organisation_id,
    )


@main.route("/services/<uuid:service_id>/make-service-live/service-name", methods=["GET", "POST"])
@user_has_permissions(allow_org_user=True)
def org_member_make_service_live_service_name(service_id):
    if current_service.live:
        return render_template("views/service-settings/service-already-live.html", prompt_to_switch_service=False), 410

    if not current_user.can_make_service_live(current_service):
        abort(403)

    form = YesNoSettingForm(name="Is the service name easy to understand?")
    if (name := request.args.get("name")) and name in {"ok", "bad"} and request.method == "GET":
        form.enabled.data = name == "ok"

    if form.validate_on_submit():
        redirect_kwargs = {"name": "ok" if form.enabled.data else "bad"}

        return redirect(
            url_for(".org_member_make_service_live_duplicate_service", service_id=current_service.id, **redirect_kwargs)
        )

    return render_template(
        "views/org-service-approver-service-name.html",
        organisation=current_service.organisation,
        form=form,
        error_summary_enabled=True,
        back_link=url_for(".org_member_make_service_live_start", service_id=current_service.id),
    )


@main.route("/services/<uuid:service_id>/make-service-live/duplicate-service", methods=["GET", "POST"])
@user_has_permissions(allow_org_user=True)
def org_member_make_service_live_duplicate_service(service_id):
    return "ok"

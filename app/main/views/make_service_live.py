from flask import abort, redirect, render_template, url_for
from flask_login import current_user

from app import current_service
from app.main import main
from app.main.forms import OnOffSettingForm
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/make-service-live", methods=["GET", "POST"])
@user_has_permissions(allow_org_user=True)
def make_service_live(service_id):

    if not current_user.can_make_service_live(current_service):
        abort(403)

    form = OnOffSettingForm(
        name="What would you like to do?",
        truthy="Approve the request and make this service live",
        falsey="Reject the request",
        thing="approve or reject",
    )

    if form.validate_on_submit():
        current_service.update_status(live=form.enabled.data)
        return redirect(url_for(".organisation_dashboard", org_id=current_service.organisation_id))

    return render_template(
        "views/make-service-live.html",
        form=form,
        title="Make service live",
    )
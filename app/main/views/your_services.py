from flask import redirect, render_template, session, url_for
from flask_login import current_user

from app import status_api_client
from app.main import main
from app.models.organisation import AllOrganisations
from app.utils import PermanentRedirect
from app.utils.user import user_is_logged_in


@main.route("/services")
def choose_service():
    raise PermanentRedirect(url_for(".your_services"))


@main.route("/services-or-dashboard")
def services_or_dashboard():
    raise PermanentRedirect(url_for(".show_accounts_or_dashboard"))


@main.route("/your-services")
@user_is_logged_in
def your_services():
    org_count, live_service_count = None, None
    if current_user.platform_admin:
        org_count, live_service_count = (
            len(AllOrganisations()),
            status_api_client.get_count_of_live_services_and_organisations()["services"],
        )
    # show headings if: user is platform admin, or there are more than two visible sections
    show_headings = (
        current_user.platform_admin
        or [
            bool(current_user.organisations),
            bool(current_user.live_services),
            bool(current_user.trial_mode_services),
        ].count(True)
        >= 2
    )
    return render_template(
        "views/your-services.html",
        can_add_service=current_user.is_gov_user,
        org_count=org_count,
        live_service_count=live_service_count,
        show_headings=show_headings,
    )


@main.route("/accounts-or-dashboard")
def show_accounts_or_dashboard():
    if not current_user.is_authenticated:
        return redirect(url_for(".index"))

    service_id = session.get("service_id")
    if service_id and (current_user.belongs_to_service(service_id) or current_user.platform_admin):
        return redirect(url_for(".service_dashboard", service_id=service_id))

    organisation_id = session.get("organisation_id")
    if organisation_id and (current_user.belongs_to_organisation(organisation_id) or current_user.platform_admin):
        return redirect(url_for(".organisation_dashboard", org_id=organisation_id))

    if len(current_user.service_ids) == 1 and not current_user.organisation_ids:
        return redirect(url_for(".service_dashboard", service_id=current_user.service_ids[0]))

    if len(current_user.organisation_ids) == 1 and not current_user.trial_mode_services:
        return redirect(url_for(".organisation_dashboard", org_id=current_user.organisation_ids[0]))

    return redirect(url_for(".your_services"))

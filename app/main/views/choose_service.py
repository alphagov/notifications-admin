from flask import redirect, render_template, session, url_for
from flask_login import current_user, login_required

from app import user_api_client
from app.main import main
from app.notify_client.service_api_client import ServicesBrowsableItem
from app.notify_client.organisations_api_client import OrganisationBrowsableItem
from app.utils import is_gov_user


@main.route("/services")
@login_required
def choose_service():
    orgs_and_services = user_api_client.get_organisations_and_services_for_user(current_user)
    from pprint import pprint
    orgs_and_services['organisations'] = [
        OrganisationBrowsableItem(org) for org in orgs_and_services['organisations']
    ]
    orgs_and_services['services_without_organisations'] = [
        ServicesBrowsableItem(x) for x in orgs_and_services['services_without_organisations']
    ]

    return render_template(
        'views/choose-service.html',
        organisations=orgs_and_services['organisations'],
        services_without_organisations=orgs_and_services['services_without_organisations'],
        can_add_service=is_gov_user(current_user.email_address)
    )


@main.route("/services-or-dashboard")
def show_all_services_or_dashboard():

    if not current_user.is_authenticated:
        return redirect(url_for('.index'))

    service_id = session.get('service_id')
    if any(service_id == x for x in current_user.services):
        return redirect(url_for('.service_dashboard', service_id=service_id))

    organisation_id = session.get('organisation_id')
    if any(organisation_id == x for x in current_user.organisations):
        return redirect(url_for('.organisation_dashboard', org_id=organisation_id))

    if len(current_user.services) == 1 and not current_user.organisations:
        return redirect(url_for('.service_dashboard', service_id=current_user.services[0]))

    if len(current_user.organisations) == 1 and not current_user.services:
        return redirect(url_for('.organisation_dashboard', org_id=current_user.organisations[0]))

    return redirect(url_for('.choose_service'))

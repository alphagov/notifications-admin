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
    pprint(orgs_and_services)
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

    services = service_api_client.get_active_services({'user_id': current_user.id})['data']

    if 1 == len(services):
        return redirect(url_for('.service_dashboard', service_id=services[0]['id']))
    else:
        service_id = session.get('service_id', None)
        if any([service_id == x['id'] for x in services]):
            return redirect(url_for('.service_dashboard', service_id=service_id))
        return redirect(url_for('.choose_service'))

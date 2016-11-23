from flask import (render_template, redirect, url_for, session)
from flask_login import login_required, current_user
from app.main import main
from app import service_api_client
from app.notify_client.service_api_client import ServicesBrowsableItem
from app.utils import is_gov_user


@main.route("/services")
@login_required
def choose_service():
    return render_template(
        'views/choose-service.html',
        services=[ServicesBrowsableItem(x) for x in
                  service_api_client.get_active_services({'user_id': current_user.id})['data']],
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

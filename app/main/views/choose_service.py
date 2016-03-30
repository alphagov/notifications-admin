from flask import (render_template, redirect, url_for, session)
from flask_login import login_required, current_user
from app.main.dao.services_dao import ServicesBrowsableItem
from app import service_api_client
from app.main import main


@main.route("/services")
@login_required
def choose_service():
    return render_template(
        'views/choose-service.html',
        services=[ServicesBrowsableItem(x) for x in service_api_client.get_services()['data']]
    )


@main.route("/services-or-dashboard")
def show_all_services_or_dashboard():

    if current_user.is_authenticated():

        services = service_api_client.get_services()['data']

        if 1 == len(services):
            return redirect(url_for('.service_dashboard', service_id=services[0]['id']))
        else:
            return redirect(url_for('.choose_service'))

    return redirect(url_for('main.index'))

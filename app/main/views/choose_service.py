from flask import (render_template, redirect, url_for)
from flask_login import login_required
from app.main.dao import services_dao
from app.main import main


@main.route("/services")
@login_required
def choose_service():
    services = services_dao.get_services()
    # If there is only one service redirect
    # to the service dashboard.
    if len(services['data']) == 1:
        return redirect(url_for(
            'main.service_dashboard', service_id=services['data'][0]['id']))
    return render_template(
        'views/choose-service.html',
        services=[services_dao.ServicesBrowsableItem(x) for x in services['data']])

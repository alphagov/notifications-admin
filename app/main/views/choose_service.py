from flask import (render_template, redirect, url_for, session)
from flask_login import login_required, current_user
from app.main.dao import services_dao
from app.main import main


@main.route("/services")
@login_required
def choose_service():
    services = services_dao.get_services(current_user.id)
    return render_template(
        'views/choose-service.html',
        services=[services_dao.ServicesBrowsableItem(x) for x in services['data']])

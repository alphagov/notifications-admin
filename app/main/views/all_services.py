from flask import render_template
from flask_login import login_required

from app import service_api_client
from app.main import main
from app.main.dao import services_dao
from app.utils import user_has_permissions


@main.route("/all-services")
@login_required
@user_has_permissions(None, admin_override=True)
def show_all_services():
    services = [services_dao.ServicesBrowsableItem(x) for x in service_api_client.get_services()['data']]
    return render_template('views/all-services.html', services=services)

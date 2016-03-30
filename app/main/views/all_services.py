from flask import render_template
from flask_login import login_required

from app import service_api_client
from app.main import main
from app.utils import user_has_permissions
from app.notify_client.api_client import ServicesBrowsableItem


@main.route("/all-services")
@login_required
@user_has_permissions(None, admin_override=True)
def show_all_services():
    services = [ServicesBrowsableItem(x) for x in service_api_client.get_services()['data']]
    return render_template('views/all-services.html', services=services)

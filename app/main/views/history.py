from flask import render_template

from app import current_service
from app.main import main
from app.utils import user_has_permissions


@main.route("/services/<service_id>/history")
@user_has_permissions('manage_service')
def history(service_id):

    return render_template(
        'views/temp-history.html',
        services=current_service.history['service_history'],
        api_keys=current_service.history['api_key_history'],
        events=current_service.history['events']
    )

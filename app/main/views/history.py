from flask import render_template

from app import service_api_client
from app.main import main
from app.utils import user_has_permissions


@main.route("/services/<service_id>/history")
@user_has_permissions('manage_service')
def history(service_id):

    data = service_api_client.get_service_history(service_id)['data']

    return render_template(
        'views/temp-history.html',
        services=data['service_history'],
        api_keys=data['api_key_history'],
        events=data['events']
    )

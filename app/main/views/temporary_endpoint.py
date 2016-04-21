from flask import (
    render_template,
    url_for
 )

from flask_login import login_required

from app.main import main

from app import (
    service_api_client,
    current_service
)

@main.route("/services/<service_id>/history")
@login_required
def service_history(service_id):
    return render_template('views/temp-history.html')

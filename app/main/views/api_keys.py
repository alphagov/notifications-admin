from flask import render_template
from flask_login import login_required
from app.main import main


@main.route("/services/<int:service_id>/api-keys")
@login_required
def api_keys(service_id):
    return render_template('views/api-keys.html', service_id=service_id)

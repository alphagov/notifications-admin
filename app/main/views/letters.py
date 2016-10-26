from flask import render_template, abort
from flask_login import login_required

from app import current_service
from app.main import main
from app.utils import user_has_permissions

@main.route("/services/<service_id>/letters")
@login_required
@user_has_permissions('manage_templates', admin_override=True)
def letters(service_id):
    return render_template('views/letters.html')

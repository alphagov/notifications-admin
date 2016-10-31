from flask import render_template, abort
from flask_login import login_required

from app import current_service
from app.main import main
from app.utils import user_has_permissions


@main.route("/services/<service_id>/letters")
@login_required
def letters(service_id):
    if not current_service['can_send_letters']:
        abort(403)
    return render_template('views/letters.html')

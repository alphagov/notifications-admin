from flask import render_template

from app.main import main
from app.utils import user_has_permissions


@main.route("/services/<service_id>/uploads")
@user_has_permissions('send_messages')
def uploads(service_id):
    return render_template('views/uploads/index.html')

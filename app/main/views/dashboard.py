from flask import (abort, render_template)
from flask_login import login_required
from app.main import main
from app.main.dao.services_dao import get_service_by_id
from client.errors import HTTPError
from ._jobs import jobs


@main.route("/services/<int:service_id>/dashboard")
@login_required
def service_dashboard(service_id):
    try:
        service = get_service_by_id(service_id)
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e
    return render_template(
        'views/service_dashboard.html',
        jobs=jobs,
        free_text_messages_remaining='25,000',
        spent_this_month='0.00',
        service_id=service_id)

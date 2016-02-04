from flask import (abort, render_template, session)
from flask_login import login_required
from app.main import main
from app.main.dao.services_dao import get_service_by_id
from app.main.dao import templates_dao
from client.errors import HTTPError
from app import job_api_client


@main.route("/services/<service_id>/dashboard")
@login_required
def service_dashboard(service_id):
    try:
        templates = templates_dao.get_service_templates(service_id)['data']
        jobs = job_api_client.get_job(service_id)['data']
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e
    try:
        service = get_service_by_id(service_id)
        session['service_name'] = service['data']['name']
    except HTTPError as e:
        if e.status_code == 404:
            abort(404)
        else:
            raise e
    return render_template(
        'views/service_dashboard.html',
        jobs=list(reversed(jobs)),
        free_text_messages_remaining='250,000',
        spent_this_month='0.00',
        template_count=len(templates),
        service_id=str(service_id))

from flask import (
    abort,
    render_template,
    session,
    flash
)

from flask_login import login_required
from app.main import main
from app.main.dao.services_dao import get_service_by_id
from app.main.dao import templates_dao
from app import job_api_client


@main.route("/services/<service_id>/dashboard")
@login_required
def service_dashboard(service_id):
    templates = templates_dao.get_service_templates(service_id)['data']
    jobs = job_api_client.get_job(service_id)['data']

    service = get_service_by_id(service_id)
    session['service_name'] = service['data']['name']
    session['service_id'] = service['data']['id']

    if session.get('invited_user'):
        session.pop('invited_user', None)
        service_name = service['data']['name']
        message = 'You have sucessfully accepted your invitation and been added to {}'.format(service_name)
        flash(message, 'default_with_tick')

    return render_template(
        'views/service_dashboard.html',
        jobs=list(reversed(jobs))[:5],
        more_jobs_to_show=(len(jobs) > 5),
        free_text_messages_remaining='250,000',
        spent_this_month='0.00',
        template_count=len(templates),
        service_id=str(service_id))

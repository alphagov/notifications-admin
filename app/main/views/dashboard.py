from flask import (
    render_template,
    session,
    flash,
    jsonify
)

from flask_login import login_required
from app.main import main
from app.main.dao import templates_dao
from app import (job_api_client, statistics_api_client, service_api_client)
from app.utils import user_has_permissions


@main.route("/services/<service_id>/dashboard")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def service_dashboard(service_id):
    templates = templates_dao.get_service_templates(service_id)['data']
    jobs = job_api_client.get_job(service_id)['data']

    service = service_api_client.get_service(service_id)
    session['service_name'] = service['data']['name']
    session['service_id'] = service['data']['id']

    if session.get('invited_user'):
        session.pop('invited_user', None)
        service_name = service['data']['name']
        message = 'You have successfully accepted your invitation and been added to {}'.format(service_name)
        flash(message, 'default_with_tick')

    statistics = statistics_api_client.get_statistics_for_service(service_id)['data']

    return render_template(
        'views/dashboard/dashboard.html',
        jobs=jobs[:5],
        more_jobs_to_show=(len(jobs) > 5),
        free_text_messages_remaining='250,000',
        spent_this_month='0.00',
        service=service['data'],
        statistics=add_rates_to(statistics),
        templates=templates,
        service_id=str(service_id))


@main.route("/services/<service_id>/dashboard.json")
@login_required
def service_dashboard_updates(service_id):

    statistics = statistics_api_client.get_statistics_for_service(service_id)['data']

    return jsonify(**{
        'today': render_template(
            'views/dashboard/today.html',
            statistics=add_rates_to(statistics),
        )
    })


def add_rates_to(delivery_statistics):

    if not delivery_statistics or not delivery_statistics[0]:
        return {}

    today = delivery_statistics[0]

    today.update({
        'emails_failure_rate': (
            "{0:.1f}".format((today['emails_error'] / today['emails_requested'] * 100))
            if today['emails_requested'] else 0
        ),
        'sms_failure_rate': (
            "{0:.1f}".format((today['sms_error'] / today['sms_requested'] * 100))
            if today['sms_requested'] else 0
        )
    })

    return today

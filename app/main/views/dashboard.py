from datetime import date
from collections import namedtuple
from itertools import groupby

from flask import (
    render_template,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

from flask_login import login_required

from app.main import main
from app import (
    job_api_client,
    statistics_api_client,
    service_api_client,
    template_statistics_client,
    current_service
)

from app.utils import user_has_permissions


@main.route("/services/<service_id>/dashboard")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def service_dashboard(service_id):
    templates = service_api_client.get_service_templates(service_id)['data']
    jobs = job_api_client.get_job(service_id)['data']

    if session.get('invited_user'):
        session.pop('invited_user', None)
        return redirect(url_for("main.tour", service_id=service_id, page=1))

    statistics = statistics_api_client.get_statistics_for_service(service_id)['data']
    template_statistics = aggregate_usage(template_statistics_client.get_template_statistics_for_service(service_id))

    return render_template(
        'views/dashboard/dashboard.html',
        jobs=jobs[:5],
        more_jobs_to_show=(len(jobs) > 5),
        free_text_messages_remaining='250,000',
        spent_this_month='0.00',
        statistics=add_rates_to(statistics),
        templates=templates,
        template_statistics=template_statistics)


@main.route("/services/<service_id>/dashboard.json")
@login_required
def service_dashboard_updates(service_id):

    statistics = statistics_api_client.get_statistics_for_service(service_id)['data']
    template_statistics = aggregate_usage(template_statistics_client.get_template_statistics_for_service(service_id))

    return jsonify(**{
        'today': render_template(
            'views/dashboard/today.html',
            statistics=add_rates_to(statistics),
            template_statistics=template_statistics
        )
    })


def add_rates_to(delivery_statistics):

    if not delivery_statistics or not delivery_statistics[0]:
        return {}

    today = None
    latest_stats = {}
    if delivery_statistics[0]['day'] == date.today().strftime('%Y-%m-%d'):
        today = delivery_statistics[0]
        latest_stats = delivery_statistics[0]

    latest_stats.update({
        'emails_failure_rate': (
            "{0:.1f}".format((float(today['emails_error']) / today['emails_requested'] * 100))
            if today and today['emails_requested'] else 0
        ),
        'sms_failure_rate': (
            "{0:.1f}".format((float(today['sms_error']) / today['sms_requested'] * 100))
            if today and today['sms_requested'] else 0
        )
    })

    return latest_stats


def aggregate_usage(template_statistics):

    immutable_template = namedtuple('Template', ['template_type', 'name', 'id'])

    # grouby requires the list to be sorted by template first
    statistics_sorted_by_template = sorted(
        (
            (
                immutable_template(**row['template']),
                row['usage_count']
            )
            for row in template_statistics
        ),
        key=lambda items: items[0]
    )

    # then group and sort the result by usage
    return sorted(
        (
            {
                'usage_count': sum(usage[1] for usage in usages),
                'template': template
            }
            for template, usages in groupby(statistics_sorted_by_template, lambda items: items[0])
        ),
        key=lambda row: row['usage_count'],
        reverse=True
    )

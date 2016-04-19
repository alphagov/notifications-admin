from datetime import date
from collections import namedtuple
from itertools import groupby
from functools import reduce

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

    if session.get('invited_user'):
        session.pop('invited_user', None)
        return redirect(url_for("main.tour", service_id=service_id, page=1))

    return render_template(
        'views/dashboard/dashboard.html',
        statistics=add_rates_to(
            statistics_api_client.get_statistics_for_service(service_id, limit_days=7)['data']
        ),
        templates=service_api_client.get_service_templates(service_id)['data'],
        template_statistics=aggregate_usage(
            template_statistics_client.get_template_statistics_for_service(service_id)
        )
    )


@main.route("/services/<service_id>/dashboard.json")
@login_required
def service_dashboard_updates(service_id):
    return jsonify(**{
        'today': render_template(
            'views/dashboard/today.html',
            statistics=add_rates_to(
                statistics_api_client.get_statistics_for_service(service_id, limit_days=7)['data']
            ),
            template_statistics=aggregate_usage(
                template_statistics_client.get_template_statistics_for_service(service_id)
            )
        )
    })


def add_rates_to(delivery_statistics):

    if not delivery_statistics or not delivery_statistics[0]:
        return {}

    sum_of_statistics = reduce(
        lambda x, y: {
            key: x.get(key, 0) + y.get(key, 0)
            for key in [
                'emails_delivered',
                'emails_requested',
                'emails_failed',
                'sms_requested',
                'sms_delivered',
                'sms_failed'
            ]
        },
        delivery_statistics
    )

    return dict(
        emails_failure_rate=(
            "{0:.1f}".format((float(sum_of_statistics['emails_failed']) / sum_of_statistics['emails_requested'] * 100))
            if sum_of_statistics.get('emails_requested') else 0
        ),
        sms_failure_rate=(
            "{0:.1f}".format((float(sum_of_statistics['sms_failed']) / sum_of_statistics['sms_requested'] * 100))
            if sum_of_statistics.get('sms_requested') else 0
        ),
        **sum_of_statistics
    )


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

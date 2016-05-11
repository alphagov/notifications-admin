from datetime import datetime, date, timedelta
from dateutil import parser
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
    statistics_api_client,
    service_api_client,
    template_statistics_client
)

from app.utils import user_has_permissions


# This is a placeholder view method to be replaced
# when product team makes decision about how/what/when
# to view history
@main.route("/services/<service_id>/history")
@login_required
def temp_service_history(service_id):
    data = service_api_client.get_service_history(service_id)['data']
    return render_template('views/temp-history.html',
                           services=data['service_history'],
                           api_keys=data['api_key_history'],
                           events=data['events'])


@main.route("/services/<service_id>/dashboard")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def service_dashboard(service_id):

    if session.get('invited_user'):
        session.pop('invited_user', None)
        session['service_id'] = service_id
        return redirect(url_for("main.tour", page=1))

    return render_template(
        'views/dashboard/dashboard.html',
        templates=service_api_client.get_service_templates(service_id)['data'],
        **get_dashboard_statistics_for_service(service_id)
    )


@main.route("/services/<service_id>/dashboard.json")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def service_dashboard_updates(service_id):
    return jsonify(**{
        'today': render_template(
            'views/dashboard/today.html',
            **get_dashboard_statistics_for_service(service_id)
        )
    })


@main.route("/services/<service_id>/template-activity")
@login_required
@user_has_permissions('view_activity', admin_override=True)
def template_history(service_id):
    template_statistics = aggregate_usage(
        template_statistics_client.get_template_statistics_for_service(service_id)
    )
    return render_template(
        'views/dashboard/all-template-statistics.html',
        template_statistics=template_statistics,
        most_used_template_count=max(
            [row['usage_count'] for row in template_statistics] or [0]
        )
    )


@main.route("/services/<service_id>/usage")
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def usage(service_id):
    return render_template(
        'views/usage.html',
        **get_dashboard_statistics_for_service(service_id)
    )


@main.route("/services/<service_id>/weekly")
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def weekly(service_id):

    earliest_date = date(2016, 4, 1)  # start of tax year
    while earliest_date.weekday() != 0:  # 0 for monday
        earliest_date -= timedelta(days=1)

    return render_template(
        'views/weekly.html',
        days=(
            add_rates_to(day) for day in
            statistics_api_client.get_7_day_aggregate_for_service(
                service_id,
                date_from=earliest_date
            )['data']
        ),
        now=datetime.utcnow()
    )


def sum_of_statistics(delivery_statistics):

    statistics_keys = (
        'emails_delivered',
        'emails_requested',
        'emails_failed',
        'sms_requested',
        'sms_delivered',
        'sms_failed'
    )

    if not delivery_statistics or not delivery_statistics[0]:
        return {
            key: 0 for key in statistics_keys
        }

    return reduce(
        lambda x, y: {
            key: x.get(key, 0) + y.get(key, 0)
            for key in statistics_keys
        },
        delivery_statistics
    )


def add_rates_to(delivery_statistics):

    return dict(
        emails_failure_rate=(
            "{0:.1f}".format(
                float(delivery_statistics['emails_failed']) / delivery_statistics['emails_requested'] * 100
            )
            if delivery_statistics['emails_requested'] else 0
        ),
        sms_failure_rate=(
            "{0:.1f}".format(
                float(delivery_statistics['sms_failed']) / delivery_statistics['sms_requested'] * 100
            )
            if delivery_statistics['sms_requested'] else 0
        ),
        week_end_datetime=parser.parse(
            delivery_statistics.get('week_end', str(datetime.utcnow()))
        ),
        **delivery_statistics
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


def get_dashboard_statistics_for_service(service_id):

    usage = service_api_client.get_service_usage(service_id)
    sms_free_allowance = 250000
    sms_rate = 0.018

    sms_sent = usage['data'].get('sms_count', 0)
    emails_sent = usage['data'].get('email_count', 0)

    template_statistics = aggregate_usage(
        template_statistics_client.get_template_statistics_for_service(service_id, limit_days=7)
    )

    return {
        'statistics': add_rates_to(sum_of_statistics(
            statistics_api_client.get_statistics_for_service(service_id, limit_days=7)['data']
        )),
        'template_statistics': template_statistics,
        'most_used_template_count': max(
            [row['usage_count'] for row in template_statistics] or [0]
        ),
        'emails_sent': emails_sent,
        'sms_free_allowance': sms_free_allowance,
        'sms_sent': sms_sent,
        'sms_allowance_remaining': max(0, (sms_free_allowance - sms_sent)),
        'sms_chargeable': max(0, sms_sent - sms_free_allowance),
        'sms_rate': sms_rate,
    }

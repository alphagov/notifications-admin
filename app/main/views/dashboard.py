from datetime import datetime, timedelta

import dateutil
from flask import (
    render_template,
    url_for,
    session,
    jsonify,
    current_app,
    request,
    abort
)
from flask_login import login_required

from app.main import main
from app import (
    job_api_client,
    service_api_client,
    template_statistics_client
)
from app.statistics_utils import get_formatted_percentage, add_rate_to_job
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

    return render_template(
        'views/dashboard/dashboard.html',
        updates_url=url_for(".service_dashboard_updates", service_id=service_id),
        templates=service_api_client.get_service_templates(service_id)['data'],
        partials=get_dashboard_partials(service_id)
    )


@main.route("/services/<service_id>/dashboard.json")
@user_has_permissions('view_activity', admin_override=True)
def service_dashboard_updates(service_id):
    return jsonify(**get_dashboard_partials(service_id))


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
            [row['count'] for row in template_statistics] or [0]
        )
    )


@main.route("/services/<service_id>/usage")
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def usage(service_id):
    try:
        year = int(request.args.get('year', 2016))
    except ValueError:
        abort(404)
    return render_template(
        'views/usage.html',
        months=get_free_paid_breakdown_for_billable_units(
            year, service_api_client.get_billable_units(service_id, year)
        ),
        year=year,
        **calculate_usage(service_api_client.get_service_usage(service_id)['data'])
    )


@main.route("/services/<service_id>/weekly")
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def weekly(service_id):
    stats = service_api_client.get_weekly_notification_stats(service_id)['data']
    return render_template(
        'views/weekly.html',
        days=format_weekly_stats_to_list(stats),
        now=datetime.utcnow()
    )


def aggregate_usage(template_statistics):
    return sorted(
        template_statistics,
        key=lambda template_statistic: template_statistic['count'],
        reverse=True
    )


def get_dashboard_partials(service_id):
    # all but scheduled and cancelled
    statuses_to_display = job_api_client.JOB_STATUSES - {'scheduled', 'cancelled'}

    template_statistics = aggregate_usage(
        template_statistics_client.get_template_statistics_for_service(service_id, limit_days=7)
    )

    scheduled_jobs = sorted(
        job_api_client.get_jobs(service_id, statuses=['scheduled'])['data'],
        key=lambda job: job['scheduled_for']
    )
    immediate_jobs = [
        add_rate_to_job(job)
        for job in job_api_client.get_jobs(service_id, limit_days=7, statuses=statuses_to_display)['data']
    ]
    service = service_api_client.get_detailed_service(service_id)

    return {
        'upcoming': render_template(
            'views/dashboard/_upcoming.html',
            scheduled_jobs=scheduled_jobs
        ),
        'totals': render_template(
            'views/dashboard/_totals.html',
            service_id=service_id,
            statistics=get_dashboard_totals(service['data']['statistics'])
        ),
        'template-statistics': render_template(
            'views/dashboard/template-statistics.html',
            template_statistics=template_statistics,
            most_used_template_count=max(
                [row['count'] for row in template_statistics] or [0]
            ),
        ),
        'has_template_statistics': bool(template_statistics),
        'jobs': render_template(
            'views/dashboard/_jobs.html',
            jobs=immediate_jobs
        ),
        'has_jobs': bool(immediate_jobs),
        'usage': render_template(
            'views/dashboard/_usage.html',
            **calculate_usage(service_api_client.get_service_usage(service_id)['data'])
        ),
    }


def get_dashboard_totals(statistics):
    for msg_type in statistics.values():
        msg_type['failed_percentage'] = get_formatted_percentage(msg_type['failed'], msg_type['requested'])
        msg_type['show_warning'] = float(msg_type['failed_percentage']) > 3
    return statistics


def calculate_usage(usage):
    # TODO: Don't hardcode these - get em from the API
    sms_free_allowance = 250000
    sms_rate = 0.0165

    sms_sent = usage.get('sms_count', 0)
    emails_sent = usage.get('email_count', 0)

    return {
        'emails_sent': emails_sent,
        'sms_free_allowance': sms_free_allowance,
        'sms_sent': sms_sent,
        'sms_allowance_remaining': max(0, (sms_free_allowance - sms_sent)),
        'sms_chargeable': max(0, sms_sent - sms_free_allowance),
        'sms_rate': sms_rate
    }


def format_weekly_stats_to_list(historical_stats):
    out = []
    for week, weekly_stats in historical_stats.items():
        for stats in weekly_stats.values():
            stats['failure_rate'] = get_formatted_percentage(stats['failed'], stats['requested'])

        week_start = dateutil.parser.parse(week)
        week_end = week_start + timedelta(days=6)
        weekly_stats.update({
            'week_start': week,
            'week_end': week_end.date().isoformat(),
            'week_end_datetime': week_end,
        })
        out.append(weekly_stats)

    return sorted(out, key=lambda x: x['week_start'], reverse=True)


def get_months_for_financial_year(year):
    return [
        month.strftime('%B')
        for month in (
            get_months_for_year(4, 13, year) +
            get_months_for_year(1, 4, year + 1)
        )
        if month < datetime.now()
    ]


def get_months_for_year(start, end, year):
    return [datetime(year, month, 1) for month in range(start, end)]


def get_free_paid_breakdown_for_billable_units(year, billable_units):
    cumulative = 0
    for month in get_months_for_financial_year(year):
        previous_cumulative = cumulative
        monthly_usage = billable_units.get(month, 0)
        cumulative += monthly_usage
        breakdown = get_free_paid_breakdown_for_month(
            cumulative, previous_cumulative, monthly_usage
        )
        yield {
            'name': month,
            'paid': breakdown['paid'],
            'free': breakdown['free']
        }


def get_free_paid_breakdown_for_month(
    cumulative,
    previous_cumulative,
    monthly_usage
):
    allowance = 250000

    if cumulative < allowance:
        return {
            'paid': 0,
            'free': monthly_usage,
        }
    elif previous_cumulative < allowance:
        return {
            'paid': monthly_usage - (allowance - previous_cumulative),
            'free': allowance - previous_cumulative
        }
    else:
        return {
            'paid': monthly_usage,
            'free': 0
        }

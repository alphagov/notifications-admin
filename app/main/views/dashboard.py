from datetime import datetime
from functools import partial
from flask import (
    render_template,
    url_for,
    session,
    jsonify,
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
from app.utils import (
    user_has_permissions,
    get_current_financial_year,
    FAILURE_STATUSES,
    REQUESTED_STATUSES,
)


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

    year, current_financial_year = requested_and_current_financial_year(request)
    stats = template_statistics_client.get_monthly_template_statistics_for_service(service_id, year)

    months = [
        {
            'name': YYYY_MM_to_datetime(month).strftime('%B'),
            'templates_used': aggregate_usage(
                format_template_stats_to_list(stats.get(month)), sort_key='requested_count'
            ),
        }
        for month in get_months_for_financial_year(year, time_format='%Y-%m')
    ]

    return render_template(
        'views/dashboard/all-template-statistics.html',
        months=months,
        most_used_template_count=max(
            max((
                template['requested_count']
                for template in month['templates_used']
            ), default=0)
            for month in months
        ),
        years=get_tuples_of_financial_years(
            partial(url_for, '.template_history', service_id=service_id),
            end=current_financial_year,
        ),
        selected_year=year,
    )


@main.route("/services/<service_id>/usage")
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def usage(service_id):
    year, current_financial_year = requested_and_current_financial_year(request)
    monthly_breakdown = get_free_paid_breakdown_for_billable_units(
        year, service_api_client.get_billable_units(service_id, year))
    return render_template(
        'views/usage.html',
        months=list(monthly_breakdown),
        selected_year=year,
        years=get_tuples_of_financial_years(
            partial(url_for, '.usage', service_id=service_id),
            start=current_financial_year - 1,
            end=current_financial_year + 1,
        ),
        # **calculate_usage(dict(monthly_breakdown))
        **calculate_usage(service_api_client.get_service_usage(service_id, year)['data'], monthly_breakdown)
    )


@main.route("/services/<service_id>/monthly")
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def monthly(service_id):
    year, current_financial_year = requested_and_current_financial_year(request)
    return render_template(
        'views/dashboard/monthly.html',
        months=format_monthly_stats_to_list(
            service_api_client.get_monthly_notification_stats(service_id, year)['data']
        ),
        years=get_tuples_of_financial_years(
            partial_url=partial(url_for, '.monthly', service_id=service_id),
            end=current_financial_year,
        ),
        selected_year=year,
    )


def aggregate_usage(template_statistics, sort_key='count'):
    return sorted(
        template_statistics,
        key=lambda template_statistic: template_statistic[sort_key],
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
            **calculate_usage(service_api_client.get_service_usage(
                service_id,
                get_current_financial_year(),
            )['data'])
        ),
    }


def get_dashboard_totals(statistics):
    for msg_type in statistics.values():
        msg_type['failed_percentage'] = get_formatted_percentage(msg_type['failed'], msg_type['requested'])
        msg_type['show_warning'] = float(msg_type['failed_percentage']) > 3
    return statistics


def calculate_usage(usage, monthly_breakdown):
    # TODO: Don't hardcode these - get em from the API
    sms_free_allowance = 250000
    sms_rate = 0.0165

    sms_sent = get_sum_units(usage.get('sms_breakdown', []))
    emails_sent = usage.get('email_count', 0)
    sms_breakdown = get_sms_breakdown_adjusted_free_allowance(
        usage.get('sms_breakdown', []), sms_free_allowance)
    return {
        'emails_sent': emails_sent,
        'sms_free_allowance': sms_free_allowance,
        'sms_sent': sms_sent,
        'sms_allowance_remaining': max(0, (sms_free_allowance - sms_sent)),
        'sms_chargeable': max(0, sms_sent - sms_free_allowance),
        'sms_rate': sms_rate,
        'sms_breakdown': sms_breakdown,
        'sms_free_units_used': usage.get('free_units_used', 0)
    }


def format_monthly_stats_to_list(historical_stats):
    return sorted((
        dict(
            date=key,
            future=YYYY_MM_to_datetime(key) > datetime.utcnow(),
            name=YYYY_MM_to_datetime(key).strftime('%B'),
            **aggregate_status_types(value)
        ) for key, value in historical_stats.items()
    ), key=lambda x: x['date'])


def YYYY_MM_to_datetime(string):
    return datetime(int(string[0:4]), int(string[5:7]), 1)


def aggregate_status_types(counts_dict):
    return get_dashboard_totals({
        '{}_counts'.format(message_type): {
            'failed': sum(
                stats.get(status, 0) for status in FAILURE_STATUSES
            ),
            'requested': sum(
                stats.get(status, 0) for status in REQUESTED_STATUSES
            )
        } for message_type, stats in counts_dict.items()
    })


def get_months_for_financial_year(year, time_format='%B'):
    return [
        month.strftime(time_format)
        for month in (
            get_months_for_year(4, 13, year) +
            get_months_for_year(1, 4, year + 1)
        )
        if month < datetime.now()
    ]


def get_months_for_year(start, end, year):
    return [datetime(year, month, 1) for month in range(start, end)]


def get_sum_billable_units(usage):
    return sum(rate['units'] * rate['multiplier'] for rate in usage)


def get_sum_units(usage):
    return sum(rate['units'] for rate in usage)


def get_sum_free_units(usage):
    return sum(rate.get('free_units', 0) * rate['multiplier'] for rate in usage)


def get_free_paid_breakdown_for_billable_units(year, billable_units):
    cumulative = 0
    for month in get_months_for_financial_year(year):
        previous_cumulative = cumulative
        monthly_usage = get_sum_billable_units(billable_units.get(month, []))
        cumulative += monthly_usage
        breakdown = get_free_paid_breakdown_for_month(
            cumulative, previous_cumulative, billable_units.get(month, [])
        )
        yield {
            'name': month,
            'paid': breakdown['paid'],
            'free': breakdown['free'],
            'sms_breakdown': breakdown.get('sms_breakdown', []),
            'free_units_used': get_sum_free_units(breakdown.get('sms_breakdown', []))
        }


def get_sms_breakdown_adjusted_free_allowance(breakdown_list, free_allowance=0):
    sms_breakdown = []

    for breakdown in breakdown_list:
        free_units = 0
        if free_allowance > 0:
            normalised_units = breakdown["units"] * breakdown["multiplier"]
            billable_units = normalised_units - free_allowance

            if billable_units <= 0:
                free_units = breakdown["units"]
                free_allowance = abs(billable_units)
            else:
                free_units = int(free_allowance / breakdown["multiplier"])

                if free_allowance < normalised_units:
                    free_allowance = 0
                else:
                    free_allowance -= normalised_units

        adj_breakdown = {
            "international": breakdown["international"],
            "free_units": free_units,
            "units": breakdown["units"] - free_units,
            "multiplier": breakdown["multiplier"]
        }
        sms_breakdown.append(adj_breakdown)

    return sms_breakdown


def get_free_paid_breakdown_for_month(
    cumulative,
    previous_cumulative,
    monthly_usage
):
    allowance = 250000

    total_monthly_billable_units = get_sum_billable_units(monthly_usage)

    if cumulative < allowance:
        return {
            'paid': 0,
            'free': total_monthly_billable_units,
        }
    elif previous_cumulative < allowance:
        remaining_allowance = allowance - previous_cumulative
        return {
            'paid': total_monthly_billable_units - remaining_allowance,
            'free': remaining_allowance,
            'sms_breakdown': get_sms_breakdown_adjusted_free_allowance(monthly_usage, remaining_allowance)
        }
    else:
        return {
            'paid': total_monthly_billable_units,
            'free': 0,
            'sms_breakdown': get_sms_breakdown_adjusted_free_allowance(monthly_usage)
        }


def requested_and_current_financial_year(request):
    try:
        return (
            int(request.args.get('year', get_current_financial_year())),
            get_current_financial_year(),
        )
    except ValueError:
        abort(404)


def format_template_stats_to_list(stats_dict):
    if not stats_dict:
        return []
    for template_id, template in stats_dict.items():
        yield dict(
            requested_count=sum(
                template['counts'].get(status, 0)
                for status in REQUESTED_STATUSES
            ),
            id=template_id,
            **template
        )


def get_tuples_of_financial_years(
    partial_url,
    start=2015,
    end=None,
):
    return (
        (
            'financial year',
            year,
            partial_url(year=year),
            '{} to {}'.format(year, year + 1),
        )
        for year in range(start, end + 1)
    )

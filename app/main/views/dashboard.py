from datetime import datetime, date, timedelta
from collections import namedtuple
from itertools import groupby

import dateutil
from flask import (
    render_template,
    url_for,
    session,
    jsonify,
    current_app
)
from flask_login import login_required

from app.main import main
from app import (
    job_api_client,
    statistics_api_client,
    service_api_client,
    template_statistics_client
)
from app.statistics_utils import add_rates_to, get_formatted_percentage, add_rate_to_jobs
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
@login_required
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
            [row['usage_count'] for row in template_statistics] or [0]
        )
    )


@main.route("/services/<service_id>/usage")
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def usage(service_id):
    return render_template(
        'views/usage.html',
        **calculate_usage(service_api_client.get_service_usage(service_id)['data'])
    )


@main.route("/services/<service_id>/weekly")
@login_required
@user_has_permissions('manage_settings', admin_override=True)
def weekly(service_id):
    stats = statistics_api_client.get_weekly_notification_stats(service_id)['data']
    return render_template(
        'views/weekly.html',
        days=format_stats_to_list(stats),
        now=datetime.utcnow()
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


def get_dashboard_partials(service_id):

    template_statistics = aggregate_usage(
        template_statistics_client.get_template_statistics_for_service(service_id, limit_days=7)
    )

    jobs = add_rate_to_jobs(filter(
        lambda job: job['original_file_name'] != current_app.config['TEST_MESSAGE_FILENAME'],
        job_api_client.get_job(service_id, limit_days=7)['data']
    ))
    service = service_api_client.get_detailed_service(service_id)

    return {
        'totals': render_template(
            'views/dashboard/_totals.html',
            service_id=service_id,
            statistics=get_dashboard_totals(service['data']['statistics'])
        ),
        'template-statistics': render_template(
            'views/dashboard/template-statistics.html',
            template_statistics=template_statistics,
            most_used_template_count=max(
                [row['usage_count'] for row in template_statistics] or [0]
            ),
        ),
        'has_template_statistics': bool(template_statistics),
        'jobs': render_template(
            'views/dashboard/_jobs.html',
            jobs=jobs
        ),
        'has_jobs': bool(jobs),
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


def format_stats_to_list(historical_stats):
    out = []
    for week, weekly_stats in historical_stats.items():
        for stats in weekly_stats.values():
            stats['failure_rate'] = get_formatted_percentage(stats['failed'], stats['requested'])

        week_start = dateutil.parser.parse(week)
        week_end = week_start + timedelta(days=6)
        item = {
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
            'week_end_datetime': week_end,
        }
        item.update(weekly_stats)
        out.append(item)

    return sorted(out, key=lambda x: x['week_start'], reverse=True)

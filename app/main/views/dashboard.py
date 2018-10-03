import calendar
from datetime import datetime
from functools import partial

from flask import (
    Response,
    abort,
    jsonify,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import redirect

from app import (
    billing_api_client,
    current_service,
    format_date_numeric,
    format_datetime_numeric,
    inbound_number_client,
    job_api_client,
    service_api_client,
    template_statistics_client,
)
from app.main import main
from app.statistics_utils import add_rate_to_job, get_formatted_percentage
from app.utils import (
    FAILURE_STATUSES,
    REQUESTED_STATUSES,
    Spreadsheet,
    generate_next_dict,
    generate_previous_dict,
    get_current_financial_year,
    user_has_permissions,
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
@user_has_permissions('view_activity', 'send_messages')
def old_service_dashboard(service_id):
    return redirect(url_for('.service_dashboard', service_id=service_id))


@main.route("/services/<service_id>")
@login_required
@user_has_permissions()
def service_dashboard(service_id):

    if session.get('invited_user'):
        session.pop('invited_user', None)
        session['service_id'] = service_id

    if not current_user.has_permissions('view_activity'):
        return redirect(url_for('main.choose_template', service_id=service_id))

    return render_template(
        'views/dashboard/dashboard.html',
        updates_url=url_for(".service_dashboard_updates", service_id=service_id),
        templates=service_api_client.get_service_templates(service_id)['data'],
        partials=get_dashboard_partials(service_id)
    )


@main.route("/services/<service_id>/dashboard.json")
@user_has_permissions('view_activity')
def service_dashboard_updates(service_id):
    return jsonify(**get_dashboard_partials(service_id))


@main.route("/services/<service_id>/template-activity")
@login_required
@user_has_permissions('view_activity')
def template_history(service_id):

    return redirect(url_for('main.template_usage', service_id=service_id), code=301)


@main.route("/services/<service_id>/template-usage")
@login_required
@user_has_permissions('view_activity')
def template_usage(service_id):

    year, current_financial_year = requested_and_current_financial_year(request)
    stats = template_statistics_client.get_monthly_template_usage_for_service(service_id, year)

    stats = sorted(stats, key=lambda x: (x['count']), reverse=True)

    def get_monthly_template_stats(month_name, stats):
        return {
            'name': month_name,
            'templates_used': [
                {
                    'id': stat['template_id'],
                    'name': stat['name'],
                    'type': stat['type'],
                    'requested_count': stat['count']
                }
                for stat in stats
                if calendar.month_name[int(stat['month'])] == month_name
            ],
        }

    months = [
        get_monthly_template_stats(month, stats)
        for month in get_months_for_financial_year(year, time_format='%B')
    ]

    return render_template(
        'views/dashboard/all-template-statistics.html',
        months=months,
        stats=stats,
        most_used_template_count=max(
            max((
                template['requested_count']
                for template in month['templates_used']
            ), default=0)
            for month in months
        ),
        years=get_tuples_of_financial_years(
            partial(url_for, '.template_usage', service_id=service_id),
            start=current_financial_year - 2,
            end=current_financial_year,
        ),
        selected_year=year
    )


@main.route("/services/<service_id>/usage")
@login_required
@user_has_permissions('manage_service')
def usage(service_id):
    year, current_financial_year = requested_and_current_financial_year(request)

    free_sms_allowance = billing_api_client.get_free_sms_fragment_limit_for_year(service_id, year)
    units = billing_api_client.get_billable_units_ft(service_id, year)
    yearly_usage = billing_api_client.get_service_usage_ft(service_id, year)

    usage_template = 'views/usage.html'
    if current_service.has_permission('letter'):
        usage_template = 'views/usage-with-letters.html'
    return render_template(
        usage_template,
        months=list(get_free_paid_breakdown_for_billable_units(
            year,
            free_sms_allowance,
            units
        )),
        selected_year=year,
        years=get_tuples_of_financial_years(
            partial(url_for, '.usage', service_id=service_id),
            start=current_financial_year - 1,
            end=current_financial_year + 1,
        ),
        **calculate_usage(yearly_usage,
                          free_sms_allowance)
    )


@main.route("/services/<service_id>/monthly")
@login_required
@user_has_permissions('view_activity')
def monthly(service_id):
    year, current_financial_year = requested_and_current_financial_year(request)
    return render_template(
        'views/dashboard/monthly.html',
        months=format_monthly_stats_to_list(
            service_api_client.get_monthly_notification_stats(service_id, year)['data']
        ),
        years=get_tuples_of_financial_years(
            partial_url=partial(url_for, '.monthly', service_id=service_id),
            start=current_financial_year - 2,
            end=current_financial_year,
        ),
        selected_year=year,
    )


@main.route("/services/<service_id>/inbox")
@login_required
@user_has_permissions('view_activity')
def inbox(service_id):

    return render_template(
        'views/dashboard/inbox.html',
        partials=get_inbox_partials(service_id),
        updates_url=url_for('.inbox_updates', service_id=service_id, page=request.args.get('page')),
    )


@main.route("/services/<service_id>/inbox.json")
@login_required
@user_has_permissions('view_activity')
def inbox_updates(service_id):

    return jsonify(get_inbox_partials(service_id))


@main.route("/services/<service_id>/inbox.csv")
@login_required
@user_has_permissions('view_activity')
def inbox_download(service_id):
    return Response(
        Spreadsheet.from_rows(
            [[
                'Phone number',
                'Message',
                'Received',
            ]] + [[
                message['user_number'],
                message['content'].lstrip(('=+-@')),
                format_datetime_numeric(message['created_at']),
            ] for message in service_api_client.get_inbound_sms(service_id)['data']]
        ).as_csv_data,
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'inline; filename="Received text messages {}.csv"'.format(
                format_date_numeric(datetime.utcnow().isoformat())
            )
        }
    )


def get_inbox_partials(service_id):
    page = int(request.args.get('page', 1))
    if not current_service.has_permission('inbound_sms'):
        abort(403)

    inbound_messages_data = service_api_client.get_most_recent_inbound_sms(service_id, page=page)
    inbound_messages = inbound_messages_data['data']

    if not inbound_messages:
        inbound_number = inbound_number_client.get_inbound_sms_number_for_service(service_id)['data']['number']
    else:
        inbound_number = None

    prev_page = None
    if page > 1:
        prev_page = generate_previous_dict('main.inbox', service_id, page)
    next_page = None
    if inbound_messages_data['has_next']:
        next_page = generate_next_dict('main.inbox', service_id, page)

    return {'messages': render_template(
        'views/dashboard/_inbox_messages.html',
        messages=inbound_messages,
        inbound_number=inbound_number,
        prev_page=prev_page,
        next_page=next_page

    )}


def aggregate_usage(template_statistics, sort_key='count'):
    return sorted(
        template_statistics,
        key=lambda template_statistic: template_statistic[sort_key],
        reverse=True
    )


def get_dashboard_partials(service_id):
    template_statistics = aggregate_usage(
        template_statistics_client.get_template_statistics_for_service(service_id, limit_days=7)
    )

    scheduled_jobs, immediate_jobs = [], []
    if job_api_client.has_jobs(service_id):
        scheduled_jobs = job_api_client.get_scheduled_jobs(service_id)
        immediate_jobs = [
            add_rate_to_job(job)
            for job in job_api_client.get_immediate_jobs(service_id)
        ]

    stats = service_api_client.get_service_statistics(service_id, today_only=False)
    column_width, max_notifiction_count = get_column_properties(
        number_of_columns=(
            3 if current_service.has_permission('letter') else 2
        )
    )
    dashboard_totals = get_dashboard_totals(stats),
    highest_notification_count = max(
        sum(
            value[key] for key in {'requested', 'failed', 'delivered'}
        )
        for key, value in dashboard_totals[0].items()
    )

    return {
        'upcoming': render_template(
            'views/dashboard/_upcoming.html',
            scheduled_jobs=scheduled_jobs
        ),
        'inbox': render_template(
            'views/dashboard/_inbox.html',
            inbound_sms_summary=(
                service_api_client.get_inbound_sms_summary(service_id)
                if current_service.has_permission('inbound_sms') else None
            ),
        ),
        'totals': render_template(
            'views/dashboard/_totals.html',
            service_id=service_id,
            statistics=dashboard_totals[0],
            column_width=column_width,
            smaller_font_size=(
                highest_notification_count > max_notifiction_count
            ),
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
        'has_jobs': bool(immediate_jobs)
    }


def get_dashboard_totals(statistics):
    for msg_type in statistics.values():
        msg_type['failed_percentage'] = get_formatted_percentage(msg_type['failed'], msg_type['requested'])
        msg_type['show_warning'] = float(msg_type['failed_percentage']) > 3
    return statistics


def calculate_usage(usage, free_sms_fragment_limit):
    sms_breakdowns = [breakdown for breakdown in usage if breakdown['notification_type'] == 'sms']

    # this relies on the assumption: only one SMS rate per financial year.
    sms_rate = 0 if len(sms_breakdowns) == 0 else sms_breakdowns[0].get("rate", 0)
    sms_sent = get_sum_billing_units(sms_breakdowns)
    sms_free_allowance = free_sms_fragment_limit

    emails = [breakdown["billing_units"] for breakdown in usage if breakdown['notification_type'] == 'email']
    emails_sent = 0 if len(emails) == 0 else emails[0]

    letters = [(breakdown["billing_units"], breakdown['letter_total']) for breakdown in usage if
               breakdown['notification_type'] == 'letter']
    letter_sent = sum(row[0] for row in letters)
    letter_cost = sum(row[1] for row in letters)

    return {
        'emails_sent': emails_sent,
        'sms_free_allowance': sms_free_allowance,
        'sms_sent': sms_sent,
        'sms_allowance_remaining': max(0, (sms_free_allowance - sms_sent)),
        'sms_chargeable': max(0, sms_sent - sms_free_allowance),
        'sms_rate': sms_rate,
        'letter_sent': letter_sent,
        'letter_cost': letter_cost
    }


def format_monthly_stats_to_list(historical_stats):
    return sorted((
        dict(
            date=key,
            future=yyyy_mm_to_datetime(key) > datetime.utcnow(),
            name=yyyy_mm_to_datetime(key).strftime('%B'),
            **aggregate_status_types(value)
        ) for key, value in historical_stats.items()
    ), key=lambda x: x['date'])


def yyyy_mm_to_datetime(string):
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


def get_sum_billing_units(billing_units, month=None):
    if month:
        return sum(b['billing_units'] for b in billing_units if b['month'] == month)
    return sum(b['billing_units'] for b in billing_units)


def get_free_paid_breakdown_for_billable_units(year, free_sms_fragment_limit, billing_units):
    cumulative = 0
    letter_cumulative = 0
    sms_units = [x for x in billing_units if x['notification_type'] == 'sms']
    letter_units = [x for x in billing_units if x['notification_type'] == 'letter']
    for month in get_months_for_financial_year(year):
        previous_cumulative = cumulative
        monthly_usage = get_sum_billing_units(sms_units, month)
        cumulative += monthly_usage
        breakdown = get_free_paid_breakdown_for_month(
            free_sms_fragment_limit, cumulative, previous_cumulative,
            [billing_month for billing_month in sms_units if billing_month['month'] == month]
        )
        letter_billing = [(x['billing_units'], x['rate'], (x['billing_units'] * x['rate']), x['postage'])
                          for x in letter_units if x['month'] == month]

        if letter_billing:
            letter_billing.sort(key=lambda x: (x[3], x[1]))

        letter_total = 0
        for x in letter_billing:
            letter_total += x[2]
            letter_cumulative += letter_total
        yield {
            'name': month,
            'letter_total': letter_total,
            'letter_cumulative': letter_cumulative,
            'paid': breakdown['paid'],
            'free': breakdown['free'],
            'letters': letter_billing
        }


def get_free_paid_breakdown_for_month(
    free_sms_fragment_limit,
    cumulative,
    previous_cumulative,
    monthly_usage
):
    allowance = free_sms_fragment_limit

    total_monthly_billing_units = get_sum_billing_units(monthly_usage)

    if cumulative < allowance:
        return {
            'paid': 0,
            'free': total_monthly_billing_units,
        }
    elif previous_cumulative < allowance:
        remaining_allowance = allowance - previous_cumulative
        return {
            'paid': total_monthly_billing_units - remaining_allowance,
            'free': remaining_allowance,
        }
    else:
        return {
            'paid': total_monthly_billing_units,
            'free': 0,
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


def get_column_properties(number_of_columns):
    return {
        2: ('column-half', 999999999),
        3: ('column-third', 99999),
    }.get(number_of_columns)

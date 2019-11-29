import itertools
import re
from collections import OrderedDict
from datetime import datetime

from flask import abort, flash, redirect, render_template, request, url_for
from notifications_python_client.errors import HTTPError

from app import (
    billing_api_client,
    complaint_api_client,
    format_date_numeric,
    letter_jobs_client,
    notification_api_client,
    platform_stats_api_client,
    service_api_client,
)
from app.extensions import redis_client
from app.main import main
from app.main.forms import (
    ClearCacheForm,
    DateFilterForm,
    RequiredDateFilterForm,
    ReturnedLettersForm,
)
from app.statistics_utils import (
    get_formatted_percentage,
    get_formatted_percentage_two_dp,
)
from app.utils import (
    Spreadsheet,
    generate_next_dict,
    generate_previous_dict,
    get_page_from_request,
    user_is_platform_admin,
)

COMPLAINT_THRESHOLD = 0.02
FAILURE_THRESHOLD = 3
ZERO_FAILURE_THRESHOLD = 0


@main.route("/platform-admin")
@user_is_platform_admin
def platform_admin():
    form = DateFilterForm(request.args, meta={'csrf': False})
    api_args = {}

    form.validate()

    if form.start_date.data:
        api_args['start_date'] = form.start_date.data
        api_args['end_date'] = form.end_date.data or datetime.utcnow().date()

    platform_stats = platform_stats_api_client.get_aggregate_platform_stats(api_args)
    number_of_complaints = complaint_api_client.get_complaint_count(api_args)

    return render_template(
        'views/platform-admin/index.html',
        form=form,
        global_stats=make_columns(platform_stats, number_of_complaints)
    )


def is_over_threshold(number, total, threshold):
    percentage = number / total * 100 if total else 0
    return percentage > threshold


def get_status_box_data(stats, key, label, threshold=FAILURE_THRESHOLD):
    return {
        'number': "{:,}".format(stats['failures'][key]),
        'label': label,
        'failing': is_over_threshold(
            stats['failures'][key],
            stats['total'],
            threshold
        ),
        'percentage': get_formatted_percentage(stats['failures'][key], stats['total'])
    }


def get_tech_failure_status_box_data(stats):
    stats = get_status_box_data(stats, 'technical-failure', 'technical failures', ZERO_FAILURE_THRESHOLD)
    stats.pop('percentage')
    return stats


def make_columns(global_stats, complaints_number):
    return [
        # email
        {
            'black_box': {
                'number': global_stats['email']['total'],
                'notification_type': 'email'
            },
            'other_data': [
                get_tech_failure_status_box_data(global_stats['email']),
                get_status_box_data(global_stats['email'], 'permanent-failure', 'permanent failures'),
                get_status_box_data(global_stats['email'], 'temporary-failure', 'temporary failures'),
                {
                    'number': complaints_number,
                    'label': 'complaints',
                    'failing': is_over_threshold(complaints_number,
                                                 global_stats['email']['total'], COMPLAINT_THRESHOLD),
                    'percentage': get_formatted_percentage_two_dp(complaints_number, global_stats['email']['total']),
                    'url': url_for('main.platform_admin_list_complaints')
                }
            ],
            'test_data': {
                'number': global_stats['email']['test-key'],
                'label': 'test emails'
            }
        },
        # sms
        {
            'black_box': {
                'number': global_stats['sms']['total'],
                'notification_type': 'sms'
            },
            'other_data': [
                get_tech_failure_status_box_data(global_stats['sms']),
                get_status_box_data(global_stats['sms'], 'permanent-failure', 'permanent failures'),
                get_status_box_data(global_stats['sms'], 'temporary-failure', 'temporary failures')
            ],
            'test_data': {
                'number': global_stats['sms']['test-key'],
                'label': 'test text messages'
            }
        },
        # letter
        {
            'black_box': {
                'number': global_stats['letter']['total'],
                'notification_type': 'letter'
            },
            'other_data': [
                get_tech_failure_status_box_data(global_stats['letter']),
                get_status_box_data(global_stats['letter'],
                                    'virus-scan-failed', 'virus scan failures', ZERO_FAILURE_THRESHOLD)
            ],
            'test_data': {
                'number': global_stats['letter']['test-key'],
                'label': 'test letters'
            }
        },
    ]


@main.route("/platform-admin/live-services", endpoint='live_services')
@main.route("/platform-admin/trial-services", endpoint='trial_services')
@user_is_platform_admin
def platform_admin_services():
    form = DateFilterForm(request.args)
    if all((
        request.args.get('include_from_test_key') is None,
        request.args.get('start_date') is None,
        request.args.get('end_date') is None,
    )):
        # Default to True if the user hasn’t done any filtering,
        # otherwise respect their choice
        form.include_from_test_key.data = True
    api_args = {'detailed': True,
                'only_active': False,    # specifically DO get inactive services
                'include_from_test_key': form.include_from_test_key.data,
                }

    if form.start_date.data:
        api_args['start_date'] = form.start_date.data
        api_args['end_date'] = form.end_date.data or datetime.utcnow().date()

    services = filter_and_sort_services(
        service_api_client.get_services(api_args)['data'],
        trial_mode_services=request.endpoint == 'main.trial_services',
    )

    return render_template(
        'views/platform-admin/services.html',
        include_from_test_key=form.include_from_test_key.data,
        form=form,
        services=list(format_stats_by_service(services)),
        page_title='{} services'.format(
            'Trial mode' if request.endpoint == 'main.trial_services' else 'Live'
        ),
        global_stats=create_global_stats(services),
    )


@main.route("/platform-admin/reports")
@user_is_platform_admin
def platform_admin_reports():
    return render_template(
        'views/platform-admin/reports.html'
    )


@main.route("/platform-admin/reports/live-services.csv")
@user_is_platform_admin
def live_services_csv():
    results = service_api_client.get_live_services_data()["data"]

    column_names = OrderedDict([
        ('service_id', 'Service ID'),
        ('organisation_name', 'Organisation'),
        ('organisation_type', 'Organisation type'),
        ('service_name', 'Service name'),
        ('consent_to_research', 'Consent to research'),
        ('contact_name', 'Main contact'),
        ('contact_email', 'Contact email'),
        ('contact_mobile', 'Contact mobile'),
        ('live_date', 'Live date'),
        ('sms_volume_intent', 'SMS volume intent'),
        ('email_volume_intent', 'Email volume intent'),
        ('letter_volume_intent', 'Letter volume intent'),
        ('sms_totals', 'SMS sent this year'),
        ('email_totals', 'Emails sent this year'),
        ('letter_totals', 'Letters sent this year'),
        ('free_sms_fragment_limit', 'Free sms allowance'),
    ])

    # initialise with header row
    live_services_data = [[x for x in column_names.values()]]

    for row in results:
        if row['live_date']:
            row['live_date'] = datetime.strptime(row["live_date"], '%a, %d %b %Y %X %Z').strftime("%d-%m-%Y")

        live_services_data.append([row[api_key] for api_key in column_names.keys()])

    return Spreadsheet.from_rows(live_services_data).as_csv_data, 200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'inline; filename="{} live services report.csv"'.format(
            format_date_numeric(datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")),
        )
    }


@main.route("/platform-admin/reports/performance-platform.xlsx")
@user_is_platform_admin
def performance_platform_xlsx():
    results = service_api_client.get_live_services_data()["data"]
    live_services_columns = ["service_id", "agency", "service_name", "_timestamp", "service", "count"]
    live_services_data = []
    live_services_data.append(live_services_columns)
    for row in results:
        live_services_data.append([
            row["service_id"],
            row["organisation_name"],
            row["service_name"],
            datetime.strptime(
                row["live_date"], '%a, %d %b %Y %X %Z'
            ).strftime("%Y-%m-%dT%H:%M:%S") + "Z" if row["live_date"] else None,
            "govuk-notify",
            1
        ])

    return Spreadsheet.from_rows(live_services_data).as_excel_file, 200, {
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'Content-Disposition': 'attachment; filename="{} performance platform report.xlsx"'.format(
            format_date_numeric(datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")),
        )
    }


@main.route("/platform-admin/reports/notifications-sent-by-service", methods=['GET', 'POST'])
@user_is_platform_admin
def notifications_sent_by_service():
    form = RequiredDateFilterForm()

    if form.validate_on_submit():
        start_date = form.start_date.data
        end_date = form.end_date.data

        headers = [
            'date_created', 'service_id', 'service_name', 'notification_type', 'count_sending', 'count_delivered',
            'count_technical_failure', 'count_temporary_failure', 'count_permanent_failure', 'count_sent'
        ]
        result = notification_api_client.get_notification_status_by_service(start_date, end_date)

        for row in result:
            row[0] = datetime.strptime(row[0], '%a, %d %b %Y %X %Z').strftime('%Y-%m-%d')

        return Spreadsheet.from_rows([headers] + result).as_csv_data, 200, {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': 'attachment; filename="{} to {} notification status per service report.csv"'.format(
                start_date, end_date)
        }

    return render_template('views/platform-admin/notifications_by_service.html', form=form)


@main.route("/platform-admin/reports/usage-for-all-services", methods=['GET', 'POST'])
@user_is_platform_admin
def usage_for_all_services():
    form = RequiredDateFilterForm()

    if form.validate_on_submit():
        start_date = form.start_date.data
        end_date = form.end_date.data
        headers = ["organisation_id", "organisation_name", "service_id", "service_name",
                   "sms_cost", "sms_fragments", "letter_cost", "letter_breakdown"]

        result = billing_api_client.get_usage_for_all_services(start_date, end_date)
        rows = [
            [
                r['organisation_id'], r["organisation_name"], r["service_id"], r["service_name"],
                r["sms_cost"], r['sms_fragments'], r["letter_cost"], r["letter_breakdown"].strip()
            ]
            for r in result
        ]
        if rows:
            return Spreadsheet.from_rows([headers] + rows).as_csv_data, 200, {
                'Content-Type': 'text/csv; charset=utf-8',
                'Content-Disposition': 'attachment; filename="Usage for all services from {} to {}.csv"'.format(
                    start_date, end_date
                )
            }
        else:
            flash('No results for dates')
    return render_template('views/platform-admin/usage_for_all_services.html', form=form)


@main.route("/platform-admin/complaints")
@user_is_platform_admin
def platform_admin_list_complaints():
    page = get_page_from_request()
    if page is None:
        abort(404, "Invalid page argument ({}).".format(request.args.get('page')))

    response = complaint_api_client.get_all_complaints(page=page)

    prev_page = None
    if response['links'].get('prev'):
        prev_page = generate_previous_dict('main.platform_admin_list_complaints', None, page)
    next_page = None
    if response['links'].get('next'):
        next_page = generate_next_dict('main.platform_admin_list_complaints', None, page)

    return render_template(
        'views/platform-admin/complaints.html',
        complaints=response['complaints'],
        page_title='All Complaints',
        page=page,
        prev_page=prev_page,
        next_page=next_page,
    )


@main.route("/platform-admin/returned-letters", methods=["GET", "POST"])
@user_is_platform_admin
def platform_admin_returned_letters():
    form = ReturnedLettersForm()

    if form.validate_on_submit():
        references = [
            re.sub('NOTIFY00[0-9]', '', r.strip())
            for r in form.references.data.split('\n')
            if r.strip()
        ]

        try:
            letter_jobs_client.submit_returned_letters(references)
        except HTTPError as error:
            if error.status_code == 400:
                error_references = [
                    re.match('references (.*) does not match', e['message']).group(1)
                    for e in error.message
                ]
                form.references.errors.append("Invalid references: {}".format(', '.join(error_references)))
            else:
                raise error
        else:
            flash('Submitted {} letter references'.format(len(references)), 'default')
            return redirect(
                url_for('.platform_admin_returned_letters')
            )
    return render_template(
        'views/platform-admin/returned-letters.html',
        form=form,
    )


@main.route("/platform-admin/clear-cache", methods=['GET', 'POST'])
@user_is_platform_admin
def clear_cache():
    # note: `service-{uuid}-templates` cache is cleared for both services and templates.
    CACHE_KEYS = OrderedDict([
        ('user', [
            'user-????????-????-????-????-????????????',
        ]),
        ('service', [
            'has_jobs-????????-????-????-????-????????????',
            'service-????????-????-????-????-????????????',
            'service-????????-????-????-????-????????????-templates',
            'service-????????-????-????-????-????????????-data-retention',
            'service-????????-????-????-????-????????????-template-folders',
        ]),
        ('template', [
            'service-????????-????-????-????-????????????-templates',
            'template-????????-????-????-????-????????????-version-*',
            'template-????????-????-????-????-????????????-versions',
        ]),
        ('email_branding', [
            'email_branding',
            'email_branding-????????-????-????-????-????????????',
        ]),
        ('letter_branding', [
            'letter_branding',
            'letter_branding-????????-????-????-????-????????????',
        ]),
        ('organisation', [
            'organisations',
            'domains',
            'live-service-and-organisation-counts',
        ]),
    ])

    form = ClearCacheForm()
    form.model_type.choices = [(key, key.replace('_', ' ').title()) for key in CACHE_KEYS]

    if form.validate_on_submit():
        to_delete = form.model_type.data

        num_deleted = max(
            redis_client.delete_cache_keys_by_pattern(pattern)
            for pattern in CACHE_KEYS[to_delete]
        )
        msg = 'Removed {} {} object{} from redis'
        flash(msg.format(num_deleted, to_delete, 's' if num_deleted != 1 else ''), category='default')

    return render_template(
        'views/platform-admin/clear-cache.html',
        form=form
    )


def sum_service_usage(service):
    total = 0
    for notification_type in service['statistics'].keys():
        total += service['statistics'][notification_type]['requested']
    return total


def filter_and_sort_services(services, trial_mode_services=False):
    return [
        service for service in sorted(
            services,
            key=lambda service: (
                service['active'],
                sum_service_usage(service),
                service['created_at']
            ),
            reverse=True,
        )
        if service['restricted'] == trial_mode_services
    ]


def create_global_stats(services):
    stats = {
        'email': {
            'delivered': 0,
            'failed': 0,
            'requested': 0
        },
        'sms': {
            'delivered': 0,
            'failed': 0,
            'requested': 0
        },
        'letter': {
            'delivered': 0,
            'failed': 0,
            'requested': 0
        }
    }
    for service in services:
        for msg_type, status in itertools.product(('sms', 'email', 'letter'), ('delivered', 'failed', 'requested')):
            stats[msg_type][status] += service['statistics'][msg_type][status]

    for stat in stats.values():
        stat['failure_rate'] = get_formatted_percentage(stat['failed'], stat['requested'])
    return stats


def format_stats_by_service(services):
    for service in services:
        yield {
            'id': service['id'],
            'name': service['name'],
            'stats': {
                msg_type: {
                    'sending': stats['requested'] - stats['delivered'] - stats['failed'],
                    'delivered': stats['delivered'],
                    'failed': stats['failed'],
                }
                for msg_type, stats in service['statistics'].items()
            },
            'restricted': service['restricted'],
            'research_mode': service['research_mode'],
            'created_at': service['created_at'],
            'active': service['active']
        }

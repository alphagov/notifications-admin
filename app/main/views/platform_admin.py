import itertools
from datetime import datetime

from flask import abort, render_template, request, url_for
from flask_login import login_required

from app import (
    complaint_api_client,
    platform_stats_api_client,
    service_api_client,
)
from app.main import main
from app.main.forms import DateFilterForm
from app.statistics_utils import (
    get_formatted_percentage,
    get_formatted_percentage_two_dp,
)
from app.utils import (
    generate_next_dict,
    generate_previous_dict,
    get_page_from_request,
    user_is_platform_admin,
)

COMPLAINT_THRESHOLD = 0.02
FAILURE_THRESHOLD = 3
ZERO_FAILURE_THRESHOLD = 0


@main.route("/platform-admin")
@login_required
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
@login_required
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


@main.route("/platform-admin/complaints")
@login_required
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

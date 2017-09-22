import itertools

from datetime import datetime
from flask import (
    render_template,
    request
)
from flask_login import login_required

from app import service_api_client
from app.main import main
from app.main.forms import DateFilterForm
from app.utils import user_has_permissions
from app.statistics_utils import get_formatted_percentage


@main.route("/platform-admin")
@login_required
@user_has_permissions(admin_override=True)
def platform_admin():
    form = DateFilterForm(request.args)
    api_args = {'detailed': True,
                'only_active': False,     # specifically DO get inactive services
                'include_from_test_key': form.include_from_test_key.data
                }

    if form.start_date.data:
        api_args['start_date'] = form.start_date.data
        api_args['end_date'] = form.end_date.data or datetime.utcnow().date()

    services = service_api_client.get_services(api_args)['data']

    return render_template(
        'views/platform-admin/index.html',
        include_from_test_key=form.include_from_test_key.data,
        form=form,
        global_stats=create_global_stats(services),
    )


@main.route("/platform-admin/live-services", endpoint='live_services')
@main.route("/platform-admin/trial-services", endpoint='trial_services')
@login_required
@user_has_permissions(admin_override=True)
def platform_admin_services():
    form = DateFilterForm(request.args)
    api_args = {'detailed': True,
                'only_active': False,    # specifically DO get inactive services
                'include_from_test_key': form.include_from_test_key.data,
                'trial_mode_services': request.endpoint == 'main.trial_services'
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
        }
    }
    # import pdb
    # pdb.set_trace()
    for service in services:
        for msg_type, status in itertools.product(('sms', 'email'), ('delivered', 'failed', 'requested')):
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

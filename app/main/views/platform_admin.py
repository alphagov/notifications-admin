import itertools

from flask import (
    render_template,
    request
)
from flask_login import login_required

from app import service_api_client
from app.main import main
from app.utils import user_has_permissions
from app.statistics_utils import get_formatted_percentage


@main.route("/platform-admin")
@login_required
@user_has_permissions(admin_override=True)
def platform_admin():
    include_from_test_key = request.args.get('include_from_test_key') != 'False'
    # specifically DO get inactive services
    api_args = {'detailed': True}
    if not include_from_test_key:
        api_args['include_from_test_key'] = False
    services = service_api_client.get_services(api_args)['data']
    return render_template(
        'views/platform-admin.html',
        include_from_test_key=include_from_test_key,
        **get_statistics(sorted(
            services,
            key=lambda service: (service['active'], service['created_at']),
            reverse=True
        ))
    )


def get_statistics(services):
    return {
        'global_stats': create_global_stats(services),
        'live_services': format_stats_by_service(
            service for service in services if not service['restricted']
        ),
        'trial_mode_services': format_stats_by_service(
            service for service in services if service['restricted']
        ),
    }


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

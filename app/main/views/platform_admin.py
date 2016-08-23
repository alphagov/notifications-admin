import itertools
from datetime import datetime

import pytz
from flask import render_template
from flask_login import login_required

from app import statistics_api_client, service_api_client
from app.main import main
from app.utils import user_has_permissions
from app.statistics_utils import get_formatted_percentage


@main.route("/platform-admin")
@login_required
@user_has_permissions(admin_override=True)
def platform_admin():
    return render_template(
        'views/platform-admin.html',
        **get_statistics()
    )


def get_statistics():
    services = service_api_client.get_services({'detailed': True})['data']
    service_stats = format_stats_by_service(services)
    return {
        'global_stats': create_global_stats(services),
        'service_stats': service_stats
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
        stats = service['statistics'].values()
        yield {
            'id': service['id'],
            'name': service['name'],
            'sending': sum((stat['requested'] - stat['delivered'] - stat['failed']) for stat in stats),
            'delivered': sum(stat['delivered'] for stat in stats),
            'failed': sum(stat['failed'] for stat in stats),
            'restricted': service['restricted'],
            'research_mode': service['research_mode']
        }

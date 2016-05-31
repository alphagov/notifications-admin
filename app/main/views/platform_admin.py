from datetime import datetime

import pytz
from flask import render_template
from flask_login import login_required

from app import statistics_api_client, service_api_client
from app.main import main
from app.utils import user_has_permissions
from app.statistics_utils import sum_of_statistics, add_rates_to


@main.route("/platform-admin")
@login_required
@user_has_permissions(admin_override=True)
def platform_admin():
    return render_template(
        'views/platform-admin.html',
        **get_statistics()
    )


def get_statistics():
    day = datetime.now(tz=pytz.timezone('Europe/London')).date()
    all_stats = statistics_api_client.get_statistics_for_all_services_for_day(day)['data']
    services = service_api_client.get_services()['data']
    service_stats = format_stats_by_service(all_stats, services)
    return {
        'global_stats': add_rates_to(sum_of_statistics(all_stats)),
        'service_stats': service_stats
    }


def format_stats_by_service(all_stats, services):
    services = {service['id']: service for service in services}
    return [
        {
            'id': stats['service'],
            'name': services[stats['service']]['name'],
            'sending': (
                (stats['sms_requested'] - stats['sms_delivered'] - stats['sms_failed']) +
                (stats['emails_requested'] - stats['emails_delivered'] - stats['emails_failed'])
            ),
            'delivered': stats['sms_delivered'] + stats['emails_delivered'],
            'failed': stats['sms_failed'] + stats['emails_failed']
        }
        for stats in all_stats
    ]

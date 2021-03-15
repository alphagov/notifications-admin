from datetime import datetime, timedelta
from itertools import groupby
from operator import itemgetter
from statistics import mean

from flask import render_template

from app import performance_dashboard_api_client, status_api_client
from app.main import main


@main.route("/performance")
def performance():
    stats = performance_dashboard_api_client.get_performance_dashboard_stats(
        start_date=(datetime.utcnow() - timedelta(days=7)).date(),
        end_date=datetime.utcnow().date(),
    )
    stats['organisations_using_notify'] = sorted(
        [
            {
                'organisation_name': organisation_name or 'No organisation',
                'count_of_live_services': len(list(group)),
            }
            for organisation_name, group in groupby(
                stats['services_using_notify'],
                itemgetter('organisation_name'),
            )
        ],
        key=itemgetter('organisation_name'),
    )
    stats['average_percentage_under_10_seconds'] = mean([
        row['percentage_under_10_seconds']
        for row in stats['processing_time']
    ] or [0])
    stats['count_of_live_services_and_organisations'] = (
        status_api_client.get_count_of_live_services_and_organisations()
    )
    return render_template(
        'views/performance.html',
        **stats
    )

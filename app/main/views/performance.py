from datetime import datetime, timedelta

from flask import render_template

from app import performance_dashboard_api_client
from app.main import main


@main.route("/performance")
def performance():
    stats = performance_dashboard_api_client.get_performance_dashboard_stats(
        start_date=(datetime.utcnow() - timedelta(days=90)).date(),
        end_date=datetime.utcnow().date(),
    )
    return render_template(
        'views/performance.html',
        **stats
    )

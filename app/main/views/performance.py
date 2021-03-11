from datetime import datetime, timedelta

from flask import jsonify

from app import performance_dashboard_api_client
from app.main import main


@main.route("/performance")
def performance():
    api_args = {}

    api_args['start_date'] = (datetime.utcnow() - timedelta(days=90)).date()
    api_args['end_date'] = datetime.utcnow().date()

    stats = performance_dashboard_api_client.get_performance_dashboard_stats(api_args)
    return jsonify(stats)

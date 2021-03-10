from datetime import datetime, timedelta

from flask import jsonify, request

from app import performance_platform_api_client
from app.main import main
from app.main.forms import DateFilterForm


@main.route("/performance-platform")
def performance_platform():
    form = DateFilterForm(request.args, meta={'csrf': False})
    api_args = {}

    form.validate()
    # default date range is 3 months
    api_args['start_date'] = form.start_date.data or datetime.utcnow().date - timedelta(months=3)
    api_args['end_date'] = form.end_date.data or datetime.utcnow().date()

    stats = performance_platform_api_client.get_performance_platform_stats(api_args)
    return jsonify(stats)

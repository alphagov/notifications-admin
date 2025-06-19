from datetime import datetime, timedelta
from itertools import groupby
from operator import itemgetter
from statistics import mean

from flask import jsonify, render_template, request

from app import performance_dashboard_api_client, status_api_client
from app.main import main
from app.main.views.sub_navigation_dictionaries import features_nav

ORGS_TO_IGNORE = ["1556fd80-a1b2-4b79-8453-f6fcb6f00d0c"]  # TODO: Move this into the database


@main.route("/features/performance")
@main.route("/features/performance.json", endpoint="performance_json")
def performance():
    stats = performance_dashboard_api_client.get_performance_dashboard_stats(
        start_date=(datetime.utcnow() - timedelta(days=7)).date(),
        end_date=datetime.utcnow().date(),
    )
    stats["services_using_notify"] = list(
        filter(lambda d: d["organisation_id"] not in ORGS_TO_IGNORE, stats["services_using_notify"])
    )
    stats["organisations_using_notify"] = sorted(
        [
            {
                "organisation_name": organisation_name or "No organisation",
                "count_of_live_services": len(list(group)),
            }
            for organisation_name, group in groupby(
                stats["services_using_notify"],
                itemgetter("organisation_name"),
            )
        ],
        key=lambda row: row["organisation_name"].lower(),
    )
    stats.pop("services_using_notify")
    stats["average_percentage_under_10_seconds"] = mean(
        [row["percentage_under_10_seconds"] for row in stats["processing_time"]] or [0]
    )
    stats["count_of_live_services_and_organisations"] = status_api_client.get_count_of_live_services_and_organisations()

    if request.endpoint == "main.performance_json":
        return jsonify(stats)

    return render_template(
        "views/guidance/features/performance.html",
        **stats,
        navigation_links=features_nav(),
    )

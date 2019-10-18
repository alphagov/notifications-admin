from collections import defaultdict

from flask import render_template

from app import current_service, format_date_numeric
from app.main import main
from app.utils import user_has_permissions


@main.route("/services/<service_id>/history")
@user_has_permissions('manage_service')
def history(service_id):
    return render_template(
        'views/temp-history.html',
        days=_chunk_events_by_day(current_service.history)
    )


def _chunk_events_by_day(events):

    days = defaultdict(list)

    for event in reversed(events):
        days[format_date_numeric(event.time)].append(event)

    return sorted(days.items(), reverse=True)

from collections import defaultdict
from operator import attrgetter

from flask import render_template, request

from app import current_service, format_date_numeric
from app.main import main
from app.models.event import APIKeyEvent, APIKeyEvents, ServiceEvents
from app.notify_client.service_api_client import service_api_client
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/history")
@user_has_permissions("manage_service")
def history(service_id):
    events = _get_events(current_service.id, request.args.get("selected"))

    return render_template(
        "views/temp-history.html",
        days=_chunk_events_by_day(events),
        show_navigation=request.args.get("selected") or any(isinstance(event, APIKeyEvent) for event in events),
        user_getter=current_service.active_users.get_name_from_id,
    )


def _get_events(service_id, selected):
    history = service_api_client.get_service_history(service_id)

    if selected == "api":
        return APIKeyEvents(history["api_key_history"])
    if selected == "service":
        return ServiceEvents(history["service_history"])
    return APIKeyEvents(history["api_key_history"]) + ServiceEvents(history["service_history"])


def _chunk_events_by_day(events):
    days = defaultdict(list)

    for event in sorted(events, key=attrgetter("time"), reverse=True):
        days[format_date_numeric(event.time)].append(event)

    return sorted(days.items(), reverse=True)

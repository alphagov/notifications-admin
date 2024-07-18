import calendar
from datetime import datetime
from functools import partial
from itertools import groupby

from flask import Response, abort, jsonify, render_template, request, session, url_for
from flask_login import current_user
from notifications_utils.recipient_validation.phone_number import format_phone_number_human_readable
from werkzeug.utils import redirect

from app import (
    billing_api_client,
    current_service,
    service_api_client,
    template_statistics_client,
    unsubscribe_requests_client,
)
from app.formatters import format_date_numeric, format_datetime_numeric
from app.main import json_updates, main
from app.statistics_utils import get_formatted_percentage
from app.utils import (
    DELIVERED_STATUSES,
    FAILURE_STATUSES,
    REQUESTED_STATUSES,
    service_has_permission,
)
from app.utils.csv import Spreadsheet
from app.utils.pagination import generate_next_dict, generate_previous_dict
from app.utils.time import get_current_financial_year
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/dashboard")
@user_has_permissions("view_activity", "send_messages")
def old_service_dashboard(service_id):
    return redirect(url_for(".service_dashboard", service_id=service_id))


@main.route("/services/<uuid:service_id>")
@user_has_permissions()
def service_dashboard(service_id):
    if session.get("invited_user_id"):
        session.pop("invited_user_id", None)
        session["service_id"] = service_id

    if not current_user.has_permissions("view_activity"):
        return redirect(url_for("main.choose_template", service_id=service_id))

    return render_template(
        "views/dashboard/dashboard.html",
        updates_url=url_for("json_updates.service_dashboard_updates", service_id=service_id),
        partials=get_dashboard_partials(service_id),
    )


@json_updates.route("/services/<uuid:service_id>/dashboard.json")
@user_has_permissions("view_activity")
def service_dashboard_updates(service_id):
    return jsonify(**get_dashboard_partials(service_id))


@main.route("/services/<uuid:service_id>/template-activity")
@user_has_permissions("view_activity")
def template_history(service_id):
    return redirect(url_for("main.template_usage", service_id=service_id), code=301)


@main.route("/services/<uuid:service_id>/template-usage")
@user_has_permissions("view_activity")
def template_usage(service_id):
    year, current_financial_year = requested_and_current_financial_year(request)
    stats = template_statistics_client.get_monthly_template_usage_for_service(service_id, year)

    stats = sorted(stats, key=lambda x: (x["count"]), reverse=True)

    def get_monthly_template_stats(month_name, stats):
        return {
            "name": month_name,
            "templates_used": [
                {
                    "id": stat["template_id"],
                    "name": stat["name"],
                    "type": stat["type"],
                    "requested_count": stat["count"],
                }
                for stat in stats
                if calendar.month_name[int(stat["month"])] == month_name
            ],
        }

    months = [
        get_monthly_template_stats(month, stats) for month in get_months_for_financial_year(year, time_format="%B")
    ]

    return render_template(
        "views/dashboard/all-template-statistics.html",
        months=months,
        stats=stats,
        most_used_template_count=max(
            max((template["requested_count"] for template in month["templates_used"]), default=0) for month in months
        ),
        years=get_tuples_of_financial_years(
            partial(url_for, "main.template_usage", service_id=service_id),
            start=current_financial_year - 2,
            end=current_financial_year,
        ),
        selected_year=year,
    )


@main.route("/services/<uuid:service_id>/usage")
@user_has_permissions("manage_service", allow_org_user=True)
def usage(service_id):
    year, current_financial_year = requested_and_current_financial_year(request)

    free_sms_allowance = billing_api_client.get_free_sms_fragment_limit_for_year(service_id, year)
    units = billing_api_client.get_monthly_usage_for_service(service_id, year)
    yearly_usage = billing_api_client.get_annual_usage_for_service(service_id, year)

    return render_template(
        "views/usage.html",
        months=list(get_monthly_usage_breakdown(year, units)),
        selected_year=year,
        years=get_tuples_of_financial_years(
            partial(url_for, ".usage", service_id=service_id),
            start=current_financial_year - 2,
            end=current_financial_year,
        ),
        **get_annual_usage_breakdown(yearly_usage, free_sms_allowance),
    )


@main.route("/services/<uuid:service_id>/monthly")
@user_has_permissions("view_activity")
def monthly(service_id):
    year, current_financial_year = requested_and_current_financial_year(request)
    return render_template(
        "views/dashboard/monthly.html",
        months=format_monthly_stats_to_list(
            service_api_client.get_monthly_notification_stats(service_id, year)["data"]
        ),
        years=get_tuples_of_financial_years(
            partial_url=partial(url_for, ".monthly", service_id=service_id),
            start=current_financial_year - 2,
            end=current_financial_year,
        ),
        selected_year=year,
    )


@main.route("/services/<uuid:service_id>/inbox")
@user_has_permissions("view_activity")
@service_has_permission("inbound_sms")
def inbox(service_id):
    return render_template(
        "views/dashboard/inbox.html",
        partials=get_inbox_partials(service_id),
        updates_url=url_for("json_updates.inbox_updates", service_id=service_id, page=request.args.get("page")),
    )


@json_updates.route("/services/<uuid:service_id>/inbox.json")
@user_has_permissions("view_activity")
@service_has_permission("inbound_sms")
def inbox_updates(service_id):
    return jsonify(get_inbox_partials(service_id))


@main.route("/services/<uuid:service_id>/inbox.csv")
@user_has_permissions("view_activity")
def inbox_download(service_id):
    return Response(
        Spreadsheet.from_rows(
            [
                [
                    "Phone number",
                    "Message",
                    "Received",
                ]
            ]
            + [
                [
                    format_phone_number_human_readable(message["user_number"]),
                    message["content"].lstrip("=+-@"),
                    format_datetime_numeric(message["created_at"]),
                ]
                for message in service_api_client.get_inbound_sms(service_id)["data"]
            ]
        ).as_csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": (
                f"inline; "
                f'filename="Received text messages {format_date_numeric(datetime.utcnow().isoformat())}.csv"'
            )
        },
    )


def get_inbox_partials(service_id):
    page = int(request.args.get("page", 1))
    inbound_messages_data = service_api_client.get_most_recent_inbound_sms(service_id, page=page)
    inbound_messages = inbound_messages_data["data"]
    if not inbound_messages:
        inbound_number = current_service.inbound_number
    else:
        inbound_number = None

    prev_page = None
    if page > 1:
        prev_page = generate_previous_dict("main.inbox", service_id, page)
    next_page = None
    if inbound_messages_data["has_next"]:
        next_page = generate_next_dict("main.inbox", service_id, page)

    return {
        "messages": render_template(
            "views/dashboard/_inbox_messages.html",
            messages=inbound_messages,
            inbound_number=inbound_number,
            prev_page=prev_page,
            next_page=next_page,
        )
    }


def filter_out_cancelled_stats(template_statistics):
    return [s for s in template_statistics if s["status"] != "cancelled"]


def aggregate_template_usage(template_statistics, sort_key="count"):
    template_statistics = filter_out_cancelled_stats(template_statistics)
    templates = []
    for k, v in groupby(sorted(template_statistics, key=lambda x: x["template_id"]), key=lambda x: x["template_id"]):
        template_stats = list(v)

        templates.append(
            {
                "template_id": k,
                "template_name": template_stats[0]["template_name"],
                "template_type": template_stats[0]["template_type"],
                "is_precompiled_letter": template_stats[0]["is_precompiled_letter"],
                "count": sum(s["count"] for s in template_stats),
            }
        )

    return sorted(templates, key=lambda x: x[sort_key], reverse=True)


def aggregate_notifications_stats(template_statistics):
    template_statistics = filter_out_cancelled_stats(template_statistics)
    notifications = {
        template_type: {status: 0 for status in ("requested", "delivered", "failed")}
        for template_type in ["sms", "email", "letter"]
    }
    for stat in template_statistics:
        notifications[stat["template_type"]]["requested"] += stat["count"]
        if stat["status"] in DELIVERED_STATUSES:
            notifications[stat["template_type"]]["delivered"] += stat["count"]
        elif stat["status"] in FAILURE_STATUSES:
            notifications[stat["template_type"]]["failed"] += stat["count"]

    return notifications


def get_dashboard_partials(service_id):
    all_statistics = template_statistics_client.get_template_statistics_for_service(service_id, limit_days=7)
    template_statistics = aggregate_template_usage(all_statistics)
    stats = aggregate_notifications_stats(all_statistics)

    dashboard_totals = (get_dashboard_totals(stats),)
    free_sms_allowance = billing_api_client.get_free_sms_fragment_limit_for_year(
        current_service.id,
        get_current_financial_year(),
    )
    yearly_usage = billing_api_client.get_annual_usage_for_service(
        service_id,
        get_current_financial_year(),
    )
    unsubscribe_requests = unsubscribe_requests_client.get_pending_unsubscribe_requests(service_id)
    return {
        "upcoming": render_template(
            "views/dashboard/_upcoming.html",
        ),
        "inbox": render_template(
            "views/dashboard/_inbox.html",
        ),
        "totals": render_template(
            "views/dashboard/_totals.html",
            service_id=service_id,
            statistics=dashboard_totals[0],
        ),
        "template-statistics": render_template(
            "views/dashboard/template-statistics.html",
            template_statistics=template_statistics,
            most_used_template_count=max([row["count"] for row in template_statistics] or [0]),
        ),
        "usage": render_template(
            "views/dashboard/_usage.html",
            **get_annual_usage_breakdown(yearly_usage, free_sms_allowance),
        ),
        "unsubscribe-requests": render_template(
            "views/dashboard/_unsubscribe-requests.html", unsubscribe_requests=unsubscribe_requests
        ),
    }


def get_dashboard_totals(statistics):
    for msg_type in statistics.values():
        msg_type["failed_percentage"] = get_formatted_percentage(msg_type["failed"], msg_type["requested"])
        msg_type["show_warning"] = float(msg_type["failed_percentage"]) > 3
    return statistics


def get_annual_usage_breakdown(usage, free_sms_fragment_limit):
    sms = get_usage_breakdown_by_type(usage, "sms")
    sms_chargeable_units = sum(row["chargeable_units"] for row in sms)
    sms_free_allowance = free_sms_fragment_limit
    sms_cost = sum(row["cost"] for row in sms)

    emails = get_usage_breakdown_by_type(usage, "email")
    emails_sent = sum(row["notifications_sent"] for row in emails)

    letters = get_usage_breakdown_by_type(usage, "letter")
    letters_sent = sum(row["notifications_sent"] for row in letters)
    letters_cost = sum(row["cost"] for row in letters)

    return {
        "emails_sent": emails_sent,
        "sms_free_allowance": sms_free_allowance,
        "sms_sent": sms_chargeable_units,
        "sms_allowance_remaining": max(0, (sms_free_allowance - sms_chargeable_units)),
        "sms_cost": sms_cost,
        "sms_breakdown": sms,
        "letter_sent": letters_sent,
        "letter_cost": letters_cost,
    }


def format_monthly_stats_to_list(historical_stats):
    return sorted(
        (
            dict(
                date=key,
                future=yyyy_mm_to_datetime(key) > datetime.utcnow(),
                name=yyyy_mm_to_datetime(key).strftime("%B"),
                **aggregate_status_types(value),
            )
            for key, value in historical_stats.items()
        ),
        key=lambda x: x["date"],
    )


def yyyy_mm_to_datetime(string):
    return datetime(int(string[0:4]), int(string[5:7]), 1)


def aggregate_status_types(counts_dict):
    return get_dashboard_totals(
        {
            f"{message_type}_counts": {
                "failed": sum(stats.get(status, 0) for status in FAILURE_STATUSES),
                "requested": sum(stats.get(status, 0) for status in REQUESTED_STATUSES),
            }
            for message_type, stats in counts_dict.items()
        }
    )


def get_months_for_financial_year(year, time_format="%B"):
    return [
        month.strftime(time_format)
        for month in (get_months_for_year(4, 13, year) + get_months_for_year(1, 4, year + 1))
        if month < datetime.now()
    ]


def get_months_for_year(start, end, year):
    return [datetime(year, month, 1) for month in range(start, end)]


def get_usage_breakdown_by_type(usage, notification_type):
    return [row for row in usage if row["notification_type"] == notification_type]


def get_monthly_usage_breakdown(year, monthly_usage):
    sms = get_usage_breakdown_by_type(monthly_usage, "sms")
    letters = get_usage_breakdown_by_type(monthly_usage, "letter")

    for month in get_months_for_financial_year(year):
        monthly_sms = [row for row in sms if row["month"] == month]
        sms_free_allowance_used = sum(row["free_allowance_used"] for row in monthly_sms)
        sms_cost = sum(row["cost"] for row in monthly_sms)
        sms_breakdown = [row for row in monthly_sms if row["charged_units"]]

        monthly_letters = [row for row in letters if row["month"] == month]
        letter_cost = sum(row["cost"] for row in monthly_letters)
        letter_breakdown = get_monthly_usage_breakdown_for_letters(monthly_letters)

        yield {
            "month": month,
            "letter_cost": letter_cost,
            "letter_breakdown": list(letter_breakdown),
            "sms_free_allowance_used": sms_free_allowance_used,
            "sms_breakdown": sms_breakdown,
            "sms_cost": sms_cost,
        }


def get_monthly_usage_breakdown_for_letters(monthly_letters):
    postage_order = {"first class": 0, "second class": 1, "international": 2}

    group_key = lambda row: (postage_order[get_monthly_usage_postage_description(row)], row["rate"])  # noqa: E731

    # First sort letter rows by postage and then by rate, clumping "europe" and
    # "rest-of-world" postage together as "international". Group the sorted rows
    # together using the same fields - "group_key" is used for both operations.
    # Note that "groupby" preserves the sort order in the groups it returns.
    rate_groups = groupby(sorted(monthly_letters, key=group_key), key=group_key)

    for _key, rate_group in rate_groups:
        # rate_group is a one-time generator so must be converted to a list for reuse
        rate_group = list(rate_group)

        yield {
            "sent": sum(x["notifications_sent"] for x in rate_group),
            "rate": rate_group[0]["rate"],
            "cost": sum(x["cost"] for x in rate_group),
            "postage_description": get_monthly_usage_postage_description(rate_group[0]),
        }


def get_monthly_usage_postage_description(row):
    if row["postage"] in ("first", "second"):
        return f'{row["postage"]} class'
    return "international"


def requested_and_current_financial_year(request):
    try:
        return (
            int(request.args.get("year", get_current_financial_year())),
            get_current_financial_year(),
        )
    except ValueError:
        abort(404)


def get_tuples_of_financial_years(
    partial_url,
    start=2015,
    end=None,
):
    return (
        (
            "financial year",
            year,
            partial_url(year=year),
            f"{year} to {year + 1}",
        )
        for year in reversed(range(start, end + 1))
    )

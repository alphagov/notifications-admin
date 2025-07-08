import calendar
from datetime import datetime
from functools import partial
from itertools import groupby

from flask import Response, abort, jsonify, render_template, request, session, url_for
from flask_login import current_user
from werkzeug.utils import redirect

from app import (
    billing_api_client,
    current_service,
    notification_api_client,
    report_request_api_client,
    service_api_client,
    template_statistics_client,
)
from app.constants import MAX_NOTIFICATION_FOR_DOWNLOAD, REPORT_REQUEST_MAX_NOTIFICATIONS
from app.extensions import redis_client
from app.formatters import format_date_numeric, format_datetime_numeric, format_phone_number_human_readable
from app.main import json_updates, main
from app.main.forms import SearchNotificationsForm
from app.models.notification import InboundSMSMessages, Notifications
from app.statistics_utils import get_formatted_percentage
from app.utils import (
    DELIVERED_STATUSES,
    FAILURE_STATUSES,
    REQUESTED_STATUSES,
    SEVEN_DAYS_TTL,
    get_sha512_hashed,
    parse_filter_args,
    service_has_permission,
    set_status_filters,
)
from app.utils.csv import Spreadsheet
from app.utils.pagination import generate_next_dict, generate_previous_dict, get_page_from_request
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


def make_cache_key(query_hash, service_id):
    return f"service-{service_id}-notification-search-query-hash-{query_hash}"


def cache_search_query(search_term, service_id, search_query_hash):
    cached_search_term = ""

    if search_query_hash:
        cached_query = redis_client.get(make_cache_key(search_query_hash, service_id))
        cached_search_term = bool(cached_query) and cached_query.decode()

    if not cached_search_term:
        search_query_hash = ""

    if search_term and search_term != cached_search_term:
        search_query_hash = get_sha512_hashed(search_term)
        redis_client.set(make_cache_key(search_query_hash, service_id), search_term, ex=SEVEN_DAYS_TTL)
        cached_search_term = search_term

    return search_query_hash, cached_search_term


def redirect_to_main_view_notification(current_service, message_type, search_query):
    return redirect(
        url_for(
            "main.view_notifications",
            service_id=current_service.id,
            message_type=message_type,
            search_query=search_query or None,
        )
    )


def post_report_request_and_redirect(current_service, report_type, message_type, status):
    # post data to create report request, get back report_request_id and then redirect
    report_request_id = report_request_api_client.create_report_request(
        current_service.id,
        report_type,
        {
            "user_id": current_user.id,
            "report_type": report_type,
            "notification_type": message_type,
            "notification_status": status,
        },
    )
    return redirect(
        url_for(
            "main.report_request",
            service_id=current_service.id,
            report_request_id=report_request_id,
        )
    )


@main.route("/services/<uuid:service_id>/notifications", methods=["GET", "POST"])
@main.route("/services/<uuid:service_id>/notifications/<template_type:message_type>", methods=["GET", "POST"])
@user_has_permissions()
def view_notifications(service_id, message_type=None):
    partials_data = _get_notifications_dashboard_partials_data(service_id, message_type)

    notifications_count = notification_api_client.get_notifications_count_for_service(
        service_id,
        message_type,
        partials_data["service_data_retention_days"],
    )

    can_download = notifications_count <= MAX_NOTIFICATION_FOR_DOWNLOAD
    download_link = None

    # Feature flag to enable request report for phase 1a deployment
    report_request_feature_flag = (
        REPORT_REQUEST_MAX_NOTIFICATIONS > 0 and notifications_count <= REPORT_REQUEST_MAX_NOTIFICATIONS
    )

    if can_download:
        download_link = url_for(
            ".download_notifications_csv",
            service_id=current_service.id,
            message_type=message_type,
            status=request.args.get("status"),
        )
    csv_report_request_type = request.form.get("report_type", "")
    csv_report_message_status = (
        "all"
        if request.args.get("status") == "sending,delivered,failed" or request.args.get("status") == ""
        else request.args.get("status", "all")
    )

    search_term = request.form.get("to", "")
    search_query_hash = request.args.get("search_query", "")
    cached_search_query_hash, cached_search_term = cache_search_query(search_term, service_id, search_query_hash)

    if request.method == "POST" and csv_report_request_type:
        return post_report_request_and_redirect(
            current_service,
            csv_report_request_type,
            message_type,
            csv_report_message_status,
        )

    if request.method == "POST" and not search_term:
        return redirect_to_main_view_notification(current_service, message_type, None)

    if cached_search_query_hash and search_query_hash != cached_search_query_hash:
        return redirect_to_main_view_notification(current_service, message_type, cached_search_query_hash)

    if not cached_search_query_hash and search_query_hash:
        cached_search_query_hash = None
        return redirect_to_main_view_notification(current_service, message_type, cached_search_query_hash)

    return render_template(
        "views/notifications.html",
        partials=partials_data,
        message_type=message_type,
        status=request.args.get("status") or "sending,delivered,failed",
        page=request.args.get("page", 1),
        search_query=cached_search_query_hash or None,
        _search_form=SearchNotificationsForm(
            message_type=message_type,
            to=cached_search_term or request.form.get("to"),
        ),
        things_you_can_search_by={
            "email": ["email address"],
            "sms": ["phone number"],
            "letter": ["postal address", "file name"],
            # We say recipient here because combining all 3 types, plus
            # reference gets too long for the hint text
            None: ["recipient"],
        }.get(message_type)
        + {
            True: ["reference"],
            False: [],
        }.get(bool(current_service.api_keys)),
        download_link=download_link,
        can_download=can_download,
        report_request_feature_flag=report_request_feature_flag,
    )


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


@json_updates.route("/services/<uuid:service_id>/notifications.json", methods=["GET", "POST"])
@json_updates.route(
    "/services/<uuid:service_id>/notifications/<template_type:message_type>.json", methods=["GET", "POST"]
)
@user_has_permissions()
def get_notifications_page_partials_as_json(service_id, message_type=None):
    return jsonify(_get_notifications_dashboard_partials_data(service_id, message_type))


def _get_notifications_dashboard_partials_data(service_id, message_type):
    page = get_page_from_request()
    if page is None:
        abort(404, f"Invalid page argument ({request.args.get('page')}).")
    filter_args = parse_filter_args(request.args)
    filter_args["status"] = set_status_filters(filter_args)
    service_data_retention_days = None
    search_term = request.form.get("to", "")

    search_query_hash = request.args.get("search_query", "")
    cached_search_query_hash, cached_search_term = cache_search_query(search_term, service_id, search_query_hash)

    if request.method == "POST" and not search_term:
        cached_search_query_hash = ""

    if message_type is not None:
        service_data_retention_days = current_service.get_days_of_retention(message_type)

    notifications = Notifications(
        service_id=service_id,
        page=page,
        template_type=[message_type] if message_type else [],
        status=filter_args.get("status"),
        limit_days=service_data_retention_days,
        to=cached_search_term or search_term,
    )
    url_args = {
        "message_type": message_type,
        "status": request.args.get("status"),
        "search_query": request.args.get("search_query"),
    }
    prev_page = None

    if notifications.prev:
        prev_page = generate_previous_dict("main.view_notifications", service_id, page, url_args=url_args)
    next_page = None

    if notifications.next:
        next_page = generate_next_dict("main.view_notifications", service_id, page, url_args)

    return {
        "service_data_retention_days": service_data_retention_days,
        "counts": render_template(
            "views/activity/counts.html",
            status=request.args.get("status"),
            status_filters=get_status_filters(
                current_service,
                message_type,
                service_api_client.get_service_statistics(service_id, limit_days=service_data_retention_days),
                search_query=cached_search_query_hash or None,
            ),
        ),
        "notifications": render_template(
            "views/activity/notifications.html",
            notifications=notifications,
            limit_days=service_data_retention_days,
            prev_page=prev_page,
            next_page=next_page,
            search_query=cached_search_query_hash or None,
            show_pagination=(not search_term),
            single_notification_url=partial(
                url_for,
                "main.view_notification",
                service_id=current_service.id,
                from_statuses=request.args.get("status"),
                from_search_query=request.args.get("search_query"),
            ),
        ),
    }


def get_status_filters(service, message_type, statistics, search_query):
    if message_type is None:
        stats = {
            key: sum(statistics[message_type][key] for message_type in {"email", "sms", "letter"})
            for key in {"requested", "delivered", "failed"}
        }
    else:
        stats = statistics[message_type]
    stats["sending"] = stats["requested"] - stats["delivered"] - stats["failed"]

    filters = [
        # key, label, option
        ("requested", "total", "sending,delivered,failed"),
        ("sending", "delivering", "sending"),
        ("delivered", "delivered", "delivered"),
        ("failed", "failed", "failed"),
    ]
    return [
        # return list containing label, option, link, count
        (
            label,
            option,
            url_for(
                "main.view_notifications",
                service_id=service.id,
                message_type=message_type,
                status=option,
                search_query=search_query,
            ),
            stats[key],
        )
        for key, label, option in filters
    ]


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
                    format_phone_number_human_readable(message.user_number),
                    message.content.lstrip("=+-@"),
                    format_datetime_numeric(message.created_at),
                ]
                for message in InboundSMSMessages(service_id)
            ]
        ).as_csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": (
                f'inline; filename="Received text messages {format_date_numeric(datetime.utcnow().isoformat())}.csv"'
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
        template_type: dict.fromkeys(("requested", "delivered", "failed"), 0)
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
    postage_order = {"first class": 0, "second class": 1, "economy mail": 2, "international": 3}

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
        return f"{row['postage']} class"
    elif row["postage"] == "economy":
        return "economy mail"
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

import dataclasses
import itertools
import re
import uuid
from datetime import datetime

from flask import abort, flash, redirect, render_template, request, url_for
from notifications_python_client.errors import HTTPError

from app import (
    billing_api_client,
    complaint_api_client,
    format_date_numeric,
    letter_jobs_client,
    notification_api_client,
    organisations_client,
    service_api_client,
    user_api_client,
)
from app.extensions import redis_client
from app.formatters import sentence_case
from app.main import main
from app.main.forms import (
    AdminClearCacheForm,
    AdminReturnedLettersForm,
    BillingReportDateFilterForm,
    PlatformAdminSearchForm,
    PlatformAdminUsersListForm,
    RequiredDateFilterForm,
)
from app.notify_client.platform_admin_api_client import admin_api_client
from app.statistics_utils import (
    get_formatted_percentage,
    get_formatted_percentage_two_dp,
)
from app.utils.csv import Spreadsheet
from app.utils.pagination import (
    generate_next_dict,
    generate_previous_dict,
    get_page_from_request,
)
from app.utils.user import user_is_platform_admin
from app.utils.user_permissions import all_ui_permissions, translate_permissions_from_db_to_ui

COMPLAINT_THRESHOLD = 0.02
FAILURE_THRESHOLD = 3
ZERO_FAILURE_THRESHOLD = 0


@main.route("/find-services-by-name", methods=["GET"])
@main.route("/find-users-by-email", methods=["GET"])
@user_is_platform_admin
def redirect_old_search_pages():
    return redirect(url_for(".platform_admin_search"))


@main.route("/platform-admin", methods=["GET", "POST"])
@user_is_platform_admin
def platform_admin_search():
    users, services, organisations = [], [], []
    search_form = PlatformAdminSearchForm()

    if search_form.validate_on_submit():
        users, services, organisations, redirect_to_something_url = [
            user_api_client.find_users_by_full_or_partial_email(search_form.search.data)["data"],
            service_api_client.find_services_by_name(search_form.search.data)["data"],
            organisations_client.search(search_form.search.data)["data"],
            get_url_for_notify_record(search_form.search.data),
        ]

        if redirect_to_something_url:
            return redirect(redirect_to_something_url)

    return render_template(
        "views/platform-admin/search.html",
        form=search_form,
        show_results=search_form.is_submitted() and search_form.search.data,
        users=users,
        services=services,
        organisations=organisations,
        error_summary_enabled=True,
    )


def is_over_threshold(number, total, threshold):
    percentage = number / total * 100 if total else 0
    return percentage > threshold


def get_status_box_data(stats, key, label, threshold=FAILURE_THRESHOLD):
    return {
        "number": f"{stats['failures'][key]:,}",
        "label": label,
        "failing": is_over_threshold(stats["failures"][key], stats["total"], threshold),
        "percentage": get_formatted_percentage(stats["failures"][key], stats["total"]),
    }


def get_tech_failure_status_box_data(stats):
    stats = get_status_box_data(stats, "technical-failure", "technical failures", ZERO_FAILURE_THRESHOLD)
    stats.pop("percentage")
    return stats


def make_columns(global_stats, complaints_number):
    return [
        # email
        {
            "black_box": {"number": global_stats["email"]["total"], "notification_type": "email"},
            "other_data": [
                get_tech_failure_status_box_data(global_stats["email"]),
                get_status_box_data(global_stats["email"], "permanent-failure", "permanent failures"),
                get_status_box_data(global_stats["email"], "temporary-failure", "temporary failures"),
                {
                    "number": complaints_number,
                    "label": "complaints",
                    "failing": is_over_threshold(
                        complaints_number, global_stats["email"]["total"], COMPLAINT_THRESHOLD
                    ),
                    "percentage": get_formatted_percentage_two_dp(complaints_number, global_stats["email"]["total"]),
                    "url": url_for("main.platform_admin_list_complaints"),
                },
            ],
            "test_data": {"number": global_stats["email"]["test-key"], "label": "test emails"},
        },
        # sms
        {
            "black_box": {"number": global_stats["sms"]["total"], "notification_type": "sms"},
            "other_data": [
                get_tech_failure_status_box_data(global_stats["sms"]),
                get_status_box_data(global_stats["sms"], "permanent-failure", "permanent failures"),
                get_status_box_data(global_stats["sms"], "temporary-failure", "temporary failures"),
            ],
            "test_data": {"number": global_stats["sms"]["test-key"], "label": "test text messages"},
        },
        # letter
        {
            "black_box": {"number": global_stats["letter"]["total"], "notification_type": "letter"},
            "other_data": [
                get_tech_failure_status_box_data(global_stats["letter"]),
                get_status_box_data(
                    global_stats["letter"], "virus-scan-failed", "virus scan failures", ZERO_FAILURE_THRESHOLD
                ),
            ],
            "test_data": {"number": global_stats["letter"]["test-key"], "label": "test letters"},
        },
    ]


@main.route("/platform-admin/reports")
@user_is_platform_admin
def platform_admin_reports():
    return render_template("views/platform-admin/reports.html")


@main.route("/platform-admin/reports/live-services.csv")
@user_is_platform_admin
def live_services_csv():
    results = service_api_client.get_live_services_data()["data"]

    column_names = {
        "service_id": "Service ID",
        "organisation_name": "Organisation",
        "organisation_type": "Organisation type",
        "service_name": "Service name",
        "consent_to_research": "Consent to research",
        "contact_name": "Main contact",
        "contact_email": "Contact email",
        "contact_mobile": "Contact mobile",
        "live_date": "Live date",
        "sms_volume_intent": "SMS volume intent",
        "email_volume_intent": "Email volume intent",
        "letter_volume_intent": "Letter volume intent",
        "sms_totals": "SMS sent this year",
        "email_totals": "Emails sent this year",
        "letter_totals": "Letters sent this year",
        "free_sms_fragment_limit": "Free sms allowance",
    }

    # initialise with header row
    live_services_data = [list(column_names.values())]

    for row in results:
        if row["live_date"]:
            row["live_date"] = datetime.strptime(row["live_date"], "%a, %d %b %Y %X %Z").strftime("%d-%m-%Y")

        live_services_data.append([row[api_key] for api_key in column_names.keys()])

    return (
        Spreadsheet.from_rows(live_services_data).as_csv_data,
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f'inline; filename="{format_date_numeric(datetime.now())} live services report.csv"',
        },
    )


@main.route("/platform-admin/reports/notifications-sent-by-service", methods=["GET", "POST"])
@user_is_platform_admin
def notifications_sent_by_service():
    form = RequiredDateFilterForm()

    if form.validate_on_submit():
        start_date = form.start_date.data
        end_date = form.end_date.data

        headers = [
            "date_created",
            "service_id",
            "service_name",
            "notification_type",
            "count_sending",
            "count_delivered",
            "count_technical_failure",
            "count_temporary_failure",
            "count_permanent_failure",
            "count_sent",
        ]
        result = notification_api_client.get_notification_status_by_service(start_date, end_date)

        return (
            Spreadsheet.from_rows([headers] + result).as_csv_data,
            200,
            {
                "Content-Type": "text/csv; charset=utf-8",
                "Content-Disposition": (
                    f'attachment; filename="{start_date} to {end_date} notification status per service report.csv"'
                ),
            },
        )

    return render_template(
        "views/platform-admin/notifications_by_service.html",
        form=form,
        error_summary_enabled=True,
    )


@main.route("/platform-admin/reports/usage-for-all-services", methods=["GET", "POST"])
@user_is_platform_admin
def get_billing_report():
    form = BillingReportDateFilterForm()

    if form.validate_on_submit():
        start_date = form.start_date.data
        end_date = form.end_date.data
        headers = [
            "organisation_id",
            "organisation_name",
            "service_id",
            "service_name",
            "sms_cost",
            "sms_chargeable_units",
            "total_letters",
            "letter_cost",
            "letter_breakdown",
            "purchase_order_number",
            "contact_names",
            "contact_email_addresses",
            "billing_reference",
        ]
        try:
            result = billing_api_client.get_data_for_billing_report(start_date, end_date)
        except HTTPError as e:
            message = "Date must be in a single financial year."
            if e.status_code == 400 and e.message == message:
                flash(message)
                return render_template("views/platform-admin/get-billing-report.html", form=form)
            else:
                raise e
        rows = [
            [
                r["organisation_id"],
                r["organisation_name"],
                r["service_id"],
                r["service_name"],
                r["sms_cost"],
                r["sms_chargeable_units"],
                r["total_letters"],
                r["letter_cost"],
                r["letter_breakdown"].strip(),
                r.get("purchase_order_number"),
                r.get("contact_names"),
                r.get("contact_email_addresses"),
                r.get("billing_reference"),
            ]
            for r in result
        ]
        if rows:
            return (
                Spreadsheet.from_rows([headers] + rows).as_csv_data,
                200,
                {
                    "Content-Type": "text/csv; charset=utf-8",
                    "Content-Disposition": f'attachment; filename="Billing Report from {start_date} to {end_date}.csv"',
                },
            )
        else:
            flash("No results for dates")
    return render_template(
        "views/platform-admin/get-billing-report.html",
        form=form,
        error_summary_enabled=True,
    )


@main.route("/platform-admin/reports/dvla-billing", methods=["GET", "POST"])
@user_is_platform_admin
def get_dvla_billing_report():
    form = BillingReportDateFilterForm()

    if form.validate_on_submit():
        start_date = form.start_date.data
        end_date = form.end_date.data
        headers = [
            "despatch date",
            "postage",
            "DVLA cost threshold",
            "sheets",
            "rate (£)",
            "letters",
            "cost (£)",
        ]
        try:
            result = billing_api_client.get_data_for_dvla_billing_report(start_date, end_date)
        except HTTPError as e:
            message = "Date must be in a single financial year."
            if e.status_code == 400 and e.message == message:
                flash(message)
                return render_template("views/platform-admin/get-dvla-billing-report.html", form=form)
            else:
                raise e
        rows = [
            [
                r["date"],
                r["postage"],
                r["cost_threshold"],
                r["sheets"],
                r["rate"],
                r["letters"],
                r["cost"],
            ]
            for r in result
        ]
        if rows:
            return (
                Spreadsheet.from_rows([headers] + rows).as_csv_data,
                200,
                {
                    "Content-Type": "text/csv; charset=utf-8",
                    "Content-Disposition": (
                        f'attachment; filename="DVLA Billing Report from {start_date} to {end_date}.csv"'
                    ),
                },
            )
        else:
            flash("No results for dates")
    return render_template("views/platform-admin/get-dvla-billing-report.html", form=form)


@main.route("/platform-admin/reports/volumes-by-service", methods=["GET", "POST"])
@user_is_platform_admin
def get_volumes_by_service():
    form = BillingReportDateFilterForm()

    if form.validate_on_submit():
        start_date = form.start_date.data
        end_date = form.end_date.data
        headers = [
            "organisation id",
            "organisation name",
            "service id",
            "service name",
            "free allowance",
            "sms notifications",
            "sms chargeable units",
            "email totals",
            "letter totals",
            "letter cost",
            "letter sheet totals",
        ]
        result = billing_api_client.get_data_for_volumes_by_service_report(start_date, end_date)

        rows = [
            [
                r["organisation_id"],
                r["organisation_name"],
                r["service_id"],
                r["service_name"],
                r["free_allowance"],
                r["sms_notifications"],
                r["sms_chargeable_units"],
                r["email_totals"],
                r["letter_totals"],
                r["letter_cost"],
                r["letter_sheet_totals"],
            ]
            for r in result
        ]
        if rows:
            return (
                Spreadsheet.from_rows([headers] + rows).as_csv_data,
                200,
                {
                    "Content-Type": "text/csv; charset=utf-8",
                    "Content-Disposition": (
                        f'attachment; filename="Volumes by service report from {start_date} to {end_date}.csv"'
                    ),
                },
            )
        else:
            flash("No results for dates")
    return render_template(
        "views/platform-admin/volumes-by-service-report.html",
        form=form,
        error_summary_enabled=True,
    )


@main.route("/platform-admin/reports/daily-volumes-report", methods=["GET", "POST"])
@user_is_platform_admin
def get_daily_volumes():
    form = BillingReportDateFilterForm()

    if form.validate_on_submit():
        start_date = form.start_date.data
        end_date = form.end_date.data
        headers = [
            "day",
            "sms totals",
            "sms fragment totals",
            "sms chargeable units",
            "email totals",
            "letter totals",
            "letter sheet totals",
        ]
        result = billing_api_client.get_data_for_daily_volumes_report(start_date, end_date)

        rows = [
            [
                r["day"],
                r["sms_totals"],
                r["sms_fragment_totals"],
                r["sms_chargeable_units"],
                r["email_totals"],
                r["letter_totals"],
                r["letter_sheet_totals"],
            ]
            for r in result
        ]
        if rows:
            return (
                Spreadsheet.from_rows([headers] + rows).as_csv_data,
                200,
                {
                    "Content-Type": "text/csv; charset=utf-8",
                    "Content-Disposition": (
                        f'attachment; filename="Daily volumes report from {start_date} to {end_date}.csv"'
                    ),
                },
            )
        else:
            flash("No results for dates")
    return render_template(
        "views/platform-admin/daily-volumes-report.html",
        form=form,
        error_summary_enabled=True,
    )


@main.route("/platform-admin/reports/daily-sms-provider-volumes-report", methods=["GET", "POST"])
@user_is_platform_admin
def get_daily_sms_provider_volumes():
    form = BillingReportDateFilterForm()

    if form.validate_on_submit():
        start_date = form.start_date.data
        end_date = form.end_date.data
        headers = [
            "day",
            "provider",
            "sms totals",
            "sms fragment totals",
            "sms chargeable units",
            "sms cost",
        ]
        result = billing_api_client.get_data_for_daily_sms_provider_volumes_report(start_date, end_date)

        rows = [
            [
                r["day"],
                r["provider"],
                r["sms_totals"],
                r["sms_fragment_totals"],
                r["sms_chargeable_units"],
                r["sms_cost"],
            ]
            for r in result
        ]
        if rows:
            return (
                Spreadsheet.from_rows([headers] + rows).as_csv_data,
                200,
                {
                    "Content-Type": "text/csv; charset=utf-8",
                    "Content-Disposition": (
                        f'attachment; filename="Daily SMS provider volumes report from {start_date} to {end_date}.csv"'
                    ),
                },
            )
        else:
            flash("No results for dates")
    return render_template(
        "views/platform-admin/daily-sms-provider-volumes-report.html",
        form=form,
        error_summary_enabled=True,
    )


@main.route("/platform-admin/complaints")
@user_is_platform_admin
def platform_admin_list_complaints():
    page = get_page_from_request()
    if page is None:
        abort(404, f"Invalid page argument ({request.args.get('page')}).")

    response = complaint_api_client.get_all_complaints(page=page)

    prev_page = None
    if response["links"].get("prev"):
        prev_page = generate_previous_dict("main.platform_admin_list_complaints", None, page)
    next_page = None
    if response["links"].get("next"):
        next_page = generate_next_dict("main.platform_admin_list_complaints", None, page)

    return render_template(
        "views/platform-admin/complaints.html",
        complaints=response["complaints"],
        page=page,
        prev_page=prev_page,
        next_page=next_page,
    )


@main.route("/platform-admin/returned-letters", methods=["GET", "POST"])
@user_is_platform_admin
def platform_admin_returned_letters():
    form = AdminReturnedLettersForm()

    if form.validate_on_submit():
        references = [re.sub("NOTIFY00[0-9]", "", r.strip()) for r in form.references.data.split("\n") if r.strip()]

        try:
            letter_jobs_client.submit_returned_letters(references)
        except HTTPError as error:
            if error.status_code == 400:
                error_references = [
                    re.match("references (.*) does not match", e["message"]).group(1) for e in error.message
                ]
                form.references.errors.append(f"Invalid references: {', '.join(error_references)}")
            else:
                raise error
        else:
            flash(f"Submitted {len(references)} letter references", "default")
            return redirect(url_for(".platform_admin_returned_letters"))
    return render_template(
        "views/platform-admin/returned-letters.html",
        form=form,
        error_summary_enabled=True,
    )


@main.route("/platform-admin/clear-cache", methods=["GET", "POST"])
@user_is_platform_admin
def clear_cache():
    # note: `service-{uuid}-templates` cache is cleared for both services and templates.
    CACHE_KEYS = {
        "user": [
            "user-????????-????-????-????-????????????",
        ],
        "service": [
            "has_jobs-????????-????-????-????-????????????",
            "service-????????-????-????-????-????????????",
            "service-????????-????-????-????-????????????-templates",
            "service-????????-????-????-????-????????????-data-retention",
            "service-????????-????-????-????-????????????-template-folders",
            "service-????????-????-????-????-????????????-returned-letters-statistics",
            "service-????????-????-????-????-????????????-returned-letters-summary",
        ],
        "template": [
            "service-????????-????-????-????-????????????-templates",
            "service-????????-????-????-????-????????????-template-????????-????-????-????-????????????-version-*",
            "service-????????-????-????-????-????????????-template-????????-????-????-????-????????????-versions",
            "service-????????-????-????-????-????????????-template-????????-????-????-????-????????????-page-count",
            "service-????????-????-????-????-????????????-template-precompiled",
        ],
        "email_branding": [
            "email_branding",
            "email_branding-????????-????-????-????-????????????",
        ],
        "letter_branding": [
            "letter_branding",
            "letter_branding-????????-????-????-????-????????????",
        ],
        "organisation": [
            "organisations",
            "domains",
            "live-service-and-organisation-counts",
            "organisation-????????-????-????-????-????????????-name",
            "organisation-????????-????-????-????-????????????-email-branding-pool",
            "organisation-????????-????-????-????-????????????-letter-branding-pool",
        ],
        "text_message_and_letter_rates": [
            "letter-rates",
            "sms-rate",
        ],
        "unsubscribe_request_reports": [
            "service-????????-????-????-????-????????????-unsubscribe-request-reports-summary",
            "service-????????-????-????-????-????????????-unsubscribe-request-statistics",
        ],
        "service_join_request": [
            "service-join-request-????????-????-????-????-????????????",
        ],
    }

    form = AdminClearCacheForm()

    form.model_type.choices = [(key, sentence_case(key.replace("_", " "))) for key in CACHE_KEYS]

    if form.validate_on_submit():
        group_keys = form.model_type.data
        groups = map(CACHE_KEYS.get, group_keys)
        patterns = list(itertools.chain(*groups))

        num_deleted = sum(redis_client.delete_by_pattern(pattern) for pattern in patterns)
        keys_deleted = ", ".join(group_keys).replace("_", " ").lower()

        msg = f"Removed {num_deleted} objects across {len(patterns)} key formats for {keys_deleted}"

        flash(msg, category="default")

    return render_template(
        "views/platform-admin/clear-cache.html",
        form=form,
        error_summary_enabled=True,
    )


def get_url_for_notify_record(uuid_):
    @dataclasses.dataclass
    class _EndpointSpec:
        endpoint: str
        param: str | None = None
        with_service_id: bool = False

        # Extra parameters to pass to `url_for`.
        extra: dict = dataclasses.field(default_factory=dict)

    try:
        uuid.UUID(uuid_)
    except ValueError:
        return None

    result, found = None, False
    try:
        result = admin_api_client.find_by_uuid(uuid_)
        found = True
    except HTTPError as e:
        if e.status_code != 404:
            raise e

    if result and found:
        url_for_data = {
            "organisation": _EndpointSpec(".organisation_dashboard", "org_id"),
            "service": _EndpointSpec(".service_dashboard", "service_id"),
            "notification": _EndpointSpec("main.view_notification", "notification_id", with_service_id=True),
            "template": _EndpointSpec("main.view_template", "template_id", with_service_id=True),
            "email_branding": _EndpointSpec(".platform_admin_update_email_branding", "branding_id"),
            "letter_branding": _EndpointSpec(".update_letter_branding", "branding_id"),
            "user": _EndpointSpec(".user_information", "user_id"),
            "provider": _EndpointSpec(".view_provider", "provider_id"),
            "reply_to_email": _EndpointSpec(".service_edit_email_reply_to", "reply_to_email_id", with_service_id=True),
            "job": _EndpointSpec(".view_job", "job_id", with_service_id=True),
            "service_contact_list": _EndpointSpec(".contact_list", "contact_list_id", with_service_id=True),
            "service_data_retention": _EndpointSpec(".edit_data_retention", "data_retention_id", with_service_id=True),
            "service_sms_sender": _EndpointSpec(".service_edit_sms_sender", "sms_sender_id", with_service_id=True),
            "inbound_number": _EndpointSpec(".inbound_sms_admin"),
            "api_key": _EndpointSpec(".api_keys", with_service_id=True),
            "template_folder": _EndpointSpec(".choose_template", "template_folder_id", with_service_id=True),
            "service_callback_api": _EndpointSpec(".api_callbacks", with_service_id=True),
            "complaint": _EndpointSpec(".platform_admin_list_complaints"),
            "inbound_sms": _EndpointSpec(
                ".conversation", "notification_id", with_service_id=True, extra={"_anchor": f"n{uuid_}"}
            ),
        }

        if not (spec := url_for_data.get(result["type"])):
            raise KeyError(f"Don't know how to redirect to {result['type']}")

        url_for_kwargs = {"endpoint": spec.endpoint, **spec.extra}

        if spec.param:
            url_for_kwargs[spec.param] = uuid_

        if spec.with_service_id:
            url_for_kwargs["service_id"] = result["context"]["service_id"]

        return url_for(**url_for_kwargs)

    return None


def sum_service_usage(service):
    total = 0
    for notification_type in service["statistics"].keys():
        total += service["statistics"][notification_type]["requested"]
    return total


def filter_and_sort_services(services, trial_mode_services=False):
    return [
        service
        for service in sorted(
            services,
            key=lambda service: (service["active"], sum_service_usage(service), service["created_at"]),
            reverse=True,
        )
        if service["restricted"] == trial_mode_services
    ]


def create_global_stats(services):
    stats = {
        "email": {"delivered": 0, "failed": 0, "requested": 0},
        "sms": {"delivered": 0, "failed": 0, "requested": 0},
        "letter": {"delivered": 0, "failed": 0, "requested": 0},
    }
    for service in services:
        for msg_type, status in itertools.product(("sms", "email", "letter"), ("delivered", "failed", "requested")):
            stats[msg_type][status] += service["statistics"][msg_type][status]

    for stat in stats.values():
        stat["failure_rate"] = get_formatted_percentage(stat["failed"], stat["requested"])
    return stats


def format_stats_by_service(services):
    for service in services:
        yield {
            "id": service["id"],
            "name": service["name"],
            "stats": service["statistics"],
            "restricted": service["restricted"],
            "created_at": service["created_at"],
            "active": service["active"],
        }


@main.route("/platform-admin/reports/users-list", methods=["GET", "POST"])
@user_is_platform_admin
def platform_admin_users_list():
    form = PlatformAdminUsersListForm()

    if not form.validate_on_submit():
        return render_template("views/platform-admin/users-list.html", form=form, error_summary_enabled=True)

    take_part_in_research = {"yes": True, "no": False}.get(form.take_part_in_research.data)

    selected_permissions = form.permissions_field.data

    def extract_date(field):
        return str(field.data) if field.data else None

    results = admin_api_client.fetch_users_list(
        created_from_date=extract_date(form.created_from_date),
        created_to_date=extract_date(form.created_to_date),
        logged_from_date=extract_date(form.logged_from_date),
        logged_to_date=extract_date(form.logged_to_date),
        take_part_in_research=take_part_in_research,
    ).get("data", [])

    if not results:
        flash("No results for filters selected")
        return render_template("views/platform-admin/users-list.html", form=form, error_summary_enabled=True)

    column_names = {
        "name": "Name",
        "email_address": "Email",
        "created_at": "Created At",
        "take_part_in_research": "Research Opt In",
        "is_team_member_of_organisation": "Is Org Team Member",
        "num_live_services": "Number of Live Services",
        "live_service_permissions": "Live Service Permissions",
    }

    live_services_data = [list(column_names.values())]

    def format_user_row(user):
        created_at = datetime.strptime(user["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d-%m-%Y")
        is_team_member_of_org = "Yes" if user.get("organisations", []) else "No"
        live_service_permissions = build_live_service_permissions_for_users_list(
            user["services"], user["permissions"], selected_permissions
        )

        return {
            "name": user["name"],
            "email_address": user["email_address"],
            "created_at": created_at,
            "take_part_in_research": "Yes" if user["take_part_in_research"] else "No",
            "is_team_member_of_organisation": is_team_member_of_org,
            "num_live_services": len(user["services"]),
            "live_service_permissions": live_service_permissions,
        }

    live_services_data.extend([list(format_user_row(user).values()) for user in results])

    return (
        Spreadsheet.from_rows(live_services_data).as_csv_data,
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f'inline; filename="{format_date_numeric(datetime.now())}_users_list.csv"',
        },
    )


def build_live_service_permissions_for_users_list(services, permissions, selected_permissions) -> str:
    """ "
    Returns a string of service_name: permissions selected on the form
    eg, "Service Name 1: manage_service, manage_users; Service Name 2: view_activity"
    """
    service_permissions = []

    if not selected_permissions:
        selected_permissions = all_ui_permissions

    service_name_lookup = {str(service["id"]): service["name"] for service in services}

    for service_id, service_perms in permissions.items():
        translated_perms = translate_permissions_from_db_to_ui(service_perms)

        filtered_permissions = translated_perms.intersection(set(selected_permissions))

        if filtered_permissions:
            service_name = service_name_lookup.get(service_id, f"Service {service_id}")
            service_permissions.append(f"{service_name}: {', '.join(filtered_permissions)}")

    return "; ".join(service_permissions)

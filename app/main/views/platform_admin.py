import itertools
import re
from collections import OrderedDict
from datetime import datetime

from flask import abort, flash, redirect, render_template, request, url_for
from notifications_python_client.errors import HTTPError

from app import (
    billing_api_client,
    complaint_api_client,
    format_date_numeric,
    letter_jobs_client,
    notification_api_client,
    platform_stats_api_client,
    service_api_client,
)
from app.extensions import redis_client
from app.main import main
from app.main.forms import (
    AdminClearCacheForm,
    AdminReturnedLettersForm,
    BillingReportDateFilterForm,
    DateFilterForm,
    PlatformAdminFindByUuidForm,
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

COMPLAINT_THRESHOLD = 0.02
FAILURE_THRESHOLD = 3
ZERO_FAILURE_THRESHOLD = 0


@main.route("/platform-admin")
@user_is_platform_admin
def platform_admin_splash_page():
    return render_template(
        "views/platform-admin/splash-page.html",
    )


@main.route("/platform-admin/find-by-uuid", methods=["GET", "POST"])
@user_is_platform_admin
def platform_admin_find_by_uuid():
    form = PlatformAdminFindByUuidForm()
    if form.validate_on_submit():
        uuid_ = form.uuid.data

        found = False
        try:
            result = admin_api_client.find_by_uuid(uuid_)
            found = True
        except HTTPError as e:
            if e.status_code != 404:
                raise e

        if found:
            url_for_data = {
                "organisation": dict(
                    endpoint=".organisation_dashboard",
                    org_id=uuid_,
                ),
                "service": dict(
                    endpoint=".service_dashboard",
                    service_id=uuid_,
                ),
                "notification": dict(
                    endpoint=".view_notification",
                    notification_id=uuid_,
                    service_id=result["context"].get("service_id"),
                ),
                "template": dict(
                    endpoint=".view_template",
                    template_id=uuid_,
                    service_id=result["context"].get("service_id"),
                ),
                "email_branding": dict(
                    endpoint=".platform_admin_update_email_branding",
                    branding_id=uuid_,
                ),
                "letter_branding": dict(
                    endpoint=".update_letter_branding",
                    branding_id=uuid_,
                ),
                "user": dict(
                    endpoint=".user_information",
                    user_id=uuid_,
                ),
                "provider": dict(
                    endpoint=".view_provider",
                    provider_id=uuid_,
                ),
                "reply_to_email": dict(
                    endpoint=".service_edit_email_reply_to",
                    reply_to_email_id=uuid_,
                    service_id=result["context"].get("service_id"),
                ),
                "job": dict(
                    endpoint=".view_job",
                    job_id=uuid_,
                    service_id=result["context"].get("service_id"),
                ),
                "service_contact_list": dict(
                    endpoint=".contact_list",
                    contact_list_id=uuid_,
                    service_id=result["context"].get("service_id"),
                ),
                "service_data_retention": dict(
                    endpoint=".edit_data_retention",
                    data_retention_id=uuid_,
                    service_id=result["context"].get("service_id"),
                ),
                "service_sms_sender": dict(
                    endpoint=".service_edit_sms_sender",
                    sms_sender_id=uuid_,
                    service_id=result["context"].get("service_id"),
                ),
                "inbound_number": dict(
                    endpoint=".inbound_sms_admin",
                ),
                "api_key": dict(
                    endpoint=".api_keys",
                    service_id=result["context"].get("service_id"),
                ),
                "template_folder": dict(
                    endpoint=".choose_template",
                    template_folder_id=uuid_,
                    service_id=result["context"].get("service_id"),
                ),
                "service_inbound_api": dict(
                    endpoint=".received_text_messages_callback",
                    service_id=result["context"].get("service_id"),
                ),
                "service_callback_api": dict(
                    endpoint=".delivery_status_callback",
                    service_id=result["context"].get("service_id"),
                ),
                "complaint": dict(
                    endpoint=".platform_admin_list_complaints",
                ),
                "inbound_sms": dict(
                    endpoint=".conversation",
                    notification_id=uuid_,
                    service_id=result["context"].get("service_id"),
                    _anchor=f"#n{uuid_}",
                ),
            }

            if not (url_for_kwargs := url_for_data.get(result["type"])):
                raise ValueError(f"Don't know how to redirect to {result['type']}")

            return redirect(url_for(**url_for_kwargs))

        form.uuid.errors.append("Could not find a thing with that UUID")

    return render_template(
        "views/platform-admin/find-by-uuid.html",
        form=form,
    )


@main.route("/platform-admin/summary")
@user_is_platform_admin
def platform_admin():
    form = DateFilterForm(request.args, meta={"csrf": False})
    api_args = {}

    form.validate()

    if form.start_date.data:
        api_args["start_date"] = form.start_date.data
        api_args["end_date"] = form.end_date.data or datetime.utcnow().date()

    platform_stats = platform_stats_api_client.get_aggregate_platform_stats(api_args)
    number_of_complaints = complaint_api_client.get_complaint_count(api_args)

    return render_template(
        "views/platform-admin/index.html", form=form, global_stats=make_columns(platform_stats, number_of_complaints)
    )


def is_over_threshold(number, total, threshold):
    percentage = number / total * 100 if total else 0
    return percentage > threshold


def get_status_box_data(stats, key, label, threshold=FAILURE_THRESHOLD):
    return {
        "number": "{:,}".format(stats["failures"][key]),
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


@main.route("/platform-admin/live-services", endpoint="live_services")
@main.route("/platform-admin/trial-services", endpoint="trial_services")
@user_is_platform_admin
def platform_admin_services():
    form = DateFilterForm(request.args)
    if all(
        (
            request.args.get("include_from_test_key") is None,
            request.args.get("start_date") is None,
            request.args.get("end_date") is None,
        )
    ):
        # Default to True if the user hasn’t done any filtering,
        # otherwise respect their choice
        form.include_from_test_key.data = True

    include_from_test_key = form.include_from_test_key.data
    api_args = {
        "detailed": True,
        "only_active": False,  # specifically DO get inactive services
        "include_from_test_key": include_from_test_key,
    }

    if form.start_date.data:
        api_args["start_date"] = form.start_date.data
        api_args["end_date"] = form.end_date.data or datetime.utcnow().date()

    services = filter_and_sort_services(
        service_api_client.get_services(api_args)["data"],
        trial_mode_services=request.endpoint == "main.trial_services",
    )

    return render_template(
        "views/platform-admin/services.html",
        include_from_test_key=include_from_test_key,
        form=form,
        services=list(format_stats_by_service(services)),
        page_title="{} services".format("Trial mode" if request.endpoint == "main.trial_services" else "Live"),
        global_stats=create_global_stats(services),
    )


@main.route("/platform-admin/reports")
@user_is_platform_admin
def platform_admin_reports():
    return render_template("views/platform-admin/reports.html")


@main.route("/platform-admin/reports/live-services.csv")
@user_is_platform_admin
def live_services_csv():
    results = service_api_client.get_live_services_data()["data"]

    column_names = OrderedDict(
        [
            ("service_id", "Service ID"),
            ("organisation_name", "Organisation"),
            ("organisation_type", "Organisation type"),
            ("service_name", "Service name"),
            ("consent_to_research", "Consent to research"),
            ("contact_name", "Main contact"),
            ("contact_email", "Contact email"),
            ("contact_mobile", "Contact mobile"),
            ("live_date", "Live date"),
            ("sms_volume_intent", "SMS volume intent"),
            ("email_volume_intent", "Email volume intent"),
            ("letter_volume_intent", "Letter volume intent"),
            ("sms_totals", "SMS sent this year"),
            ("email_totals", "Emails sent this year"),
            ("letter_totals", "Letters sent this year"),
            ("free_sms_fragment_limit", "Free sms allowance"),
        ]
    )

    # initialise with header row
    live_services_data = [[x for x in column_names.values()]]

    for row in results:
        if row["live_date"]:
            row["live_date"] = datetime.strptime(row["live_date"], "%a, %d %b %Y %X %Z").strftime("%d-%m-%Y")

        live_services_data.append([row[api_key] for api_key in column_names.keys()])

    return (
        Spreadsheet.from_rows(live_services_data).as_csv_data,
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": 'inline; filename="{} live services report.csv"'.format(
                format_date_numeric(datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")),
            ),
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
                    'attachment; filename="{} to {} notification status per service report.csv"'.format(
                        start_date, end_date
                    )
                ),
            },
        )

    return render_template("views/platform-admin/notifications_by_service.html", form=form)


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
                    "Content-Disposition": 'attachment; filename="Billing Report from {} to {}.csv"'.format(
                        start_date, end_date
                    ),
                },
            )
        else:
            flash("No results for dates")
    return render_template("views/platform-admin/get-billing-report.html", form=form)


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
                    "Content-Disposition": 'attachment; filename="Volumes by service report from {} to {}.csv"'.format(
                        start_date, end_date
                    ),
                },
            )
        else:
            flash("No results for dates")
    return render_template("views/platform-admin/volumes-by-service-report.html", form=form)


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
                    "Content-Disposition": 'attachment; filename="Daily volumes report from {} to {}.csv"'.format(
                        start_date, end_date
                    ),
                },
            )
        else:
            flash("No results for dates")
    return render_template("views/platform-admin/daily-volumes-report.html", form=form)


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
    return render_template("views/platform-admin/daily-sms-provider-volumes-report.html", form=form)


@main.route("/platform-admin/complaints")
@user_is_platform_admin
def platform_admin_list_complaints():
    page = get_page_from_request()
    if page is None:
        abort(404, "Invalid page argument ({}).".format(request.args.get("page")))

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
            redis_client.delete_by_pattern("service-????????-????-????-????-????????????-returned-letters-statistics")
            redis_client.delete_by_pattern("service-????????-????-????-????-????????????-returned-letters-summary")
        except HTTPError as error:
            if error.status_code == 400:
                error_references = [
                    re.match("references (.*) does not match", e["message"]).group(1) for e in error.message
                ]
                form.references.errors.append("Invalid references: {}".format(", ".join(error_references)))
            else:
                raise error
        else:
            flash("Submitted {} letter references".format(len(references)), "default")
            return redirect(url_for(".platform_admin_returned_letters"))
    return render_template(
        "views/platform-admin/returned-letters.html",
        form=form,
    )


@main.route("/platform-admin/clear-cache", methods=["GET", "POST"])
@user_is_platform_admin
def clear_cache():
    # note: `service-{uuid}-templates` cache is cleared for both services and templates.
    CACHE_KEYS = OrderedDict(
        [
            (
                "user",
                [
                    "user-????????-????-????-????-????????????",
                ],
            ),
            (
                "service",
                [
                    "has_jobs-????????-????-????-????-????????????",
                    "service-????????-????-????-????-????????????",
                    "service-????????-????-????-????-????????????-templates",
                    "service-????????-????-????-????-????????????-data-retention",
                    "service-????????-????-????-????-????????????-template-folders",
                    "service-????????-????-????-????-????????????-returned-letters-statistics",
                    "service-????????-????-????-????-????????????-returned-letters-summary",
                ],
            ),
            (
                "template",
                [
                    "service-????????-????-????-????-????????????-templates",
                    "service-????????-????-????-????-????????????-template-????????-????-????-????-????????????-version-*",  # noqa
                    "service-????????-????-????-????-????????????-template-????????-????-????-????-????????????-versions",  # noqa
                ],
            ),
            (
                "email_branding",
                [
                    "email_branding",
                    "email_branding-????????-????-????-????-????????????",
                ],
            ),
            (
                "letter_branding",
                [
                    "letter_branding",
                    "letter_branding-????????-????-????-????-????????????",
                ],
            ),
            (
                "organisation",
                [
                    "organisations",
                    "domains",
                    "live-service-and-organisation-counts",
                    "organisation-????????-????-????-????-????????????-name",
                    "organisation-????????-????-????-????-????????????-email-branding-pool",
                    "organisation-????????-????-????-????-????????????-letter-branding-pool",
                ],
            ),
            (
                "broadcast",
                [
                    "service-????????-????-????-????-????????????-broadcast-message-????????-????-????-????-????????????",  # noqa
                ],
            ),
        ]
    )

    form = AdminClearCacheForm()

    form.model_type.choices = [(key, key.replace("_", " ").title()) for key in CACHE_KEYS]

    if form.validate_on_submit():
        group_keys = form.model_type.data
        groups = map(CACHE_KEYS.get, group_keys)
        patterns = list(itertools.chain(*groups))

        num_deleted = sum(redis_client.delete_by_pattern(pattern) for pattern in patterns)

        msg = f"Removed {num_deleted} objects across {len(patterns)} key formats " f'for {", ".join(group_keys)}'

        flash(msg, category="default")

    return render_template("views/platform-admin/clear-cache.html", form=form)


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

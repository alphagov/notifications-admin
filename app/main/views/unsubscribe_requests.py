from flask import flash, redirect, render_template, request, url_for

from app import current_service, format_date_numeric, service_api_client, unsubscribe_api_client
from app.main import main
from app.main.forms import ProcessUnsubscribeRequestForm
from app.models.spreadsheet import Spreadsheet
from app.utils import hide_from_search_engines
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/unsubscribe-requests/summary")
@user_has_permissions("view_activity")
def unsubscribe_request_reports_summary(service_id):
    return render_template("views/unsubscribe-request-reports-summary.html")


@main.route("/services/<uuid:service_id>/unsubscribe-requests/reports/latest")
@main.route("/services/<uuid:service_id>/unsubscribe-requests/reports/<uuid:batch_id>", methods=["GET", "POST"])
@user_has_permissions("view_activity")
def unsubscribe_request_report(service_id, batch_id=None):
    if batch_id:
        report = current_service.unsubscribe_request_reports_summary.get_by_batch_id(batch_id)
    else:
        report = current_service.unsubscribe_request_reports_summary.get_unbatched_report()
    form = ProcessUnsubscribeRequestForm(
        is_a_batched_report=report.is_a_batched_report,
        report_completed=report.completed,
        report_has_been_processed=report.completed,
    )

    if form.validate_on_submit():
        report_has_been_processed = form.data["report_has_been_processed"]
        data = {"report_has_been_processed": report_has_been_processed}
        service_api_client.process_unsubscribe_request_report(service_id, batch_id=batch_id, data=data)
        flash(
            f"Report for {report.title} marked as {'completed' if report_has_been_processed else 'not completed'}",
            "default_with_tick",
        )
        return redirect(url_for("main.unsubscribe_request_reports_summary", service_id=service_id, batch_id=batch_id))
    return render_template(
        "views/unsubscribe-request-report.html",
        report=report,
        form=form,
        error_summary_enabled=True,
    )


@main.route("/services/<uuid:service_id>/unsubscribe-requests/reports/download")
@main.route("/services/<uuid:service_id>/unsubscribe-requests/reports/download/<uuid:batch_id>.csv")
@user_has_permissions("view_activity")
def download_unsubscribe_request_report(service_id, batch_id=None):
    if not batch_id:
        return redirect(url_for("main.create_unsubscribe_request_report", service_id=service_id))

    report = service_api_client.get_unsubscribe_request_report(service_id, batch_id)
    column_names = {
        "email_address": "Email address",
        "template_name": "Template name",
        "original_file_name": "Uploaded spreadsheet file name",
        "template_sent_at": "Template sent at",
        "unsubscribe_request_received_at": "Unsubscribe request received at",
    }
    # initialise with header row
    data = [list(column_names.values())]
    for row in report["unsubscribe_requests"]:
        data.append([row[key] for key in column_names.keys()])
    return (
        Spreadsheet.from_rows(data).as_csv_data,
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f'attachment; filename="Email unsubscribe requests '
            f"{format_date_numeric(report['earliest_timestamp'])} "
            f"to {format_date_numeric(report['latest_timestamp'])}.csv",
        },
    )


@main.route("/services/<uuid:service_id>/unsubscribe-requests/reports/batch-report")
@user_has_permissions("view_activity", restrict_admin_usage=True)
def create_unsubscribe_request_report(service_id):
    created_report_id = current_service.unsubscribe_request_reports_summary.batch_unbatched()
    return redirect(
        url_for(
            "main.unsubscribe_request_report",
            service_id=service_id,
            batch_id=created_report_id,
            force_download="true",
        )
    )


@main.route("/unsubscribe/<uuid:notification_id>/<string:token>", methods=["GET", "POST"])
@hide_from_search_engines
def unsubscribe(notification_id, token):
    if request.method == "POST":
        if not unsubscribe_api_client.unsubscribe(notification_id, token):
            return render_template("views/unsubscribe-failed.html"), 404

        return redirect(url_for("main.unsubscribe_confirmed"))

    return render_template("views/unsubscribe.html")


@main.route("/unsubscribe/confirmed")
@hide_from_search_engines
def unsubscribe_confirmed():
    return render_template("views/unsubscribe.html", confirmed=True)


@main.route("/unsubscribe/example", methods=["GET", "POST"])
@hide_from_search_engines
def unsubscribe_example():
    if request.method == "POST":
        return redirect(url_for("main.unsubscribe_example_confirmed"))

    return render_template("views/unsubscribe.html", example=True)


@main.route("/unsubscribe/example/confirmed")
@hide_from_search_engines
def unsubscribe_example_confirmed():
    return render_template("views/unsubscribe.html", example=True, confirmed=True)

from flask import flash, redirect, render_template, url_for

from app import current_service, format_date_normal, service_api_client
from app.main import main
from app.main.forms import ProcessUnsubscribeRequestForm
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
        message = f"""Report for {format_date_normal(report.earliest_timestamp)} until  \
                  {format_date_normal(report.latest_timestamp)} has been marked as \
                  {'Completed' if report_has_been_processed else 'not completed.'}"""
        flash(message, "default_with_tick")
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
    else:
        pass

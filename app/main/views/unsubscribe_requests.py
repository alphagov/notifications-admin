from flask import render_template, url_for, redirect, flash
from notifications_python_client.errors import HTTPError

from app import current_service, service_api_client
from app.main import main
from app.main.forms import ProcessUnsubscribeRequestForm
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/unsubscribe-requests/summary")
@user_has_permissions("view_activity")
def unsubscribe_request_reports_summary(service_id):
    return render_template("views/unsubscribe-request-reports-summary.html")


@main.route("/services/<uuid:service_id>/unsubscribe-requests/reports/latest")
@main.route("/services/<uuid:service_id>/unsubscribe-requests/reports/<uuid:batch_id>", methods=['GET', 'POST'])
@user_has_permissions("view_activity")
def unsubscribe_request_report(service_id, batch_id=None):
    if batch_id:
        report = current_service.unsubscribe_request_reports_summary.get_by_batch_id(batch_id)
    else:
        report = current_service.unsubscribe_request_reports_summary.get_unbatched_report()
    form = ProcessUnsubscribeRequestForm(is_a_batched_report=report.is_a_batched_report,
                                         report_status=report.status)

    if form.validate_on_submit():
        try:
            service_api_client.process_unsubscribe_request_report(service_id, batch_id=batch_id, data=None)
            message = "Report has been marked as Completed"
            flash(message, "default_with_tick")
            return render_template(
                                    "views/unsubscribe-request-report.html",
                                    report=report,
                                    form=form,
                                    error_summary_enabled=True,
                                )
        except HTTPError as http_error:
            if http_error.status_code == 400 and http_error.message.get("batch_id"):
                if http_error.message.get("batch_id"):
                    error_message = "This report is not available"
                    form.report_has_been_processed.errors.append(error_message)
            else:
                raise http_error
    return render_template(
        "views/unsubscribe-request-report.html",
        report=report,
        form=form,
        error_summary_enabled=True,
    )

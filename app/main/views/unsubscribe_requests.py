from flask import abort, render_template

from app import current_service
from app.main import main
from app.main.forms import ProcessUnsubscribeRequestForm
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/unsubscribe-requests/summary")
@user_has_permissions("view_activity")
def unsubscribe_request_reports_summary(service_id):
    reports_summary_data = _get_unsubscribe_request_reports_summary()
    return render_template("views/unsubscribe-request-reports-summary.html", data=reports_summary_data)


def _get_unsubscribe_request_reports_summary():
    data = current_service.unsubscribe_request_reports_summary
    reports_summary_data = []
    if unbatched_report_summary := data["unbatched_report_summary"]:
        reports_summary_data.append(unbatched_report_summary)
    if batched_reports_summaries := data["batched_reports_summaries"]:
        reports_summary_data += batched_reports_summaries
    return reports_summary_data


@main.route("/services/<uuid:service_id>/unsubscribe-requests/reports/<uuid:batch_id>")
@user_has_permissions("view_activity")
def unsubscribe_request_report(service_id, batch_id):
    report_data = None
    if reports_summary_data := _get_unsubscribe_request_reports_summary():
        for report_summary in reports_summary_data:
            if report_summary["batch_id"] == batch_id:
                report_data = report_summary
        if report_data:
            form = ProcessUnsubscribeRequestForm(is_a_batched_report=report_data["is_a_batched_report"])
            return render_template(
                "views/unsubscribe-request-report.html",
                count=report_data["count"],
                earliest_timestamp=report_data["earliest_timestamp"],
                latest_timestamp=report_data["latest_timestamp"],
                processed_by_service_at=report_data["processed_by_service_at"],
                batch_id=report_data["batch_id"],
                is_a_batched_report=report_data["is_a_batched_report"],
                service_id=service_id,
                form=form,
            )

    abort(404)

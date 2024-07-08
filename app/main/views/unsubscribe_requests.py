from flask import render_template, redirect, url_for

from app import current_service, service_api_client
from app.main import main
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/unsubscribe-request-reports-summary")
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


@main.route("/services/<uuid:service_id>/unsubscribe-request-report/<uuid:report_id>")
@user_has_permissions("view_activity")
def unsubscribe_request_report(service_id, report_id):
    reports_summary_data = _get_unsubscribe_request_reports_summary()
    for report_summary in reports_summary_data:
        if report_summary["report_id"] == report_id:
            return render_template(
                "views/unsubscribe-request-report.html",
                count=report_summary["count"],
                earliest_timestamp=report_summary["earliest_timestamp"],
                latest_timestamp=report_summary["latest_timestamp"],
                processed_by_service_at=report_summary["processed_by_service_at"],
                report_id=report_summary["report_id"],
                is_a_batched_report=report_summary["is_a_batched_report"],
                service_id=service_id,
            )

        else:
            return redirect(url_for('main.unsubscribe_request_reports_summary'))

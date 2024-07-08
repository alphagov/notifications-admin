from flask import render_template

from app import current_service
from app.main import main
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/unsubscribe-request-reports-summary")
@user_has_permissions("view_activity")
def unsubscribe_request_reports_summary(service_id):
    data = current_service.unsubscribe_request_reports_summary
    batched_reports_summaries = data["batched_reports_summaries"]
    unbatched_report_summary = data["unbatched_report_summary"]
    reports_summary_data = [unbatched_report_summary] + batched_reports_summaries
    return render_template("views/unsubscribe-request-reports-summary.html", data=reports_summary_data)

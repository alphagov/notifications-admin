from flask import abort, render_template

from app import current_service
from app.main import main
from app.main.forms import ProcessUnsubscribeRequestForm
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/unsubscribe-requests/summary")
@user_has_permissions("view_activity")
def unsubscribe_request_reports_summary(service_id):
    return render_template("views/unsubscribe-request-reports-summary.html")


@main.route("/services/<uuid:service_id>/unsubscribe-requests/reports/<uuid:batch_id>")
@user_has_permissions("view_activity")
def unsubscribe_request_report(service_id, batch_id):
    report = current_service.unsubscribe_request_reports_summary.get_by_batch_id(batch_id)
    if not report:
        abort(404)

    form = ProcessUnsubscribeRequestForm(is_a_batched_report=report.is_a_batched_report)
    return render_template(
        "views/unsubscribe-request-report.html",
        report=report,
        form=form,
    )

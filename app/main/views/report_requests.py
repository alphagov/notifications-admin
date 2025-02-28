from flask import abort, send_file
from flask_login import current_user

from app.constants import REPORT_REQUEST_STORED
from app.main import main
from app.models.report_request import ReportRequest
from app.utils.user import user_is_platform_admin


@main.route("/services/<uuid:service_id>/report-request/<uuid:report_request_id>.csv")
@user_is_platform_admin
def report_request_download(service_id, report_request_id):
    report_request = ReportRequest.from_id(service_id, report_request_id)

    if report_request.user_id != current_user.id:
        abort(403)

    if report_request.status != REPORT_REQUEST_STORED:
        abort(404)

    file_contents = ReportRequest.download(report_request_id)

    return send_file(
        path_or_file=file_contents,
        download_name=f"{report_request_id}.csv",
        as_attachment=True,
    )

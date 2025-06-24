from flask import abort, jsonify, render_template, send_file, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError
from werkzeug.utils import redirect

from app import current_service
from app.constants import REPORT_REQUEST_FAILED, REPORT_REQUEST_MAX_NOTIFICATIONS, REPORT_REQUEST_STORED
from app.main import main
from app.models.report_request import ReportRequest
from app.utils.user import user_has_permissions


def validate_report_request_enabled():
    if REPORT_REQUEST_MAX_NOTIFICATIONS == 0 and not current_user.platform_admin:
        abort(403)


@main.route("/services/<uuid:service_id>/download-report/<uuid:report_request_id>", methods=["GET"])
@user_has_permissions("view_activity")
def report_request(service_id, report_request_id):
    validate_report_request_enabled()

    try:
        report_request = ReportRequest.from_id(service_id, report_request_id)
    except HTTPError as e:
        if e.status_code == 404:
            return render_template(
                "views/csv-report/unavailable.html",
            )
        else:
            raise e

    if report_request.user_id != current_user.id:
        abort(403)
    # if they refresh that page manually before JS does
    # or they copy and paste that url in manually or bookmark it
    # we redirect them to the download page
    if report_request.status == REPORT_REQUEST_STORED:
        return redirect(
            url_for(
                "main.report_ready",
                service_id=service_id,
                report_request_id=report_request.id,
            )
        )

    if report_request.status == REPORT_REQUEST_FAILED:
        return render_template(
            "views/csv-report/error.html",
        )

    return render_template(
        "views/csv-report/preparing.html",
        retention_period=current_service.get_days_of_retention(report_request.parameter["notification_type"]),
        report_request=report_request,
    )


@main.route("/services/<uuid:service_id>/download-report/<uuid:report_request_id>/ready", methods=["GET"])
@user_has_permissions("view_activity")
def report_ready(service_id, report_request_id):
    validate_report_request_enabled()

    if not ReportRequest.exists_in_s3(report_request_id):
        return render_template(
            "views/csv-report/unavailable.html",
        )

    try:
        report_request = ReportRequest.from_id(service_id, report_request_id)
    except HTTPError as e:
        if e.status_code == 404:
            # if the report is no longer available, show them "No longer available page"
            return redirect(
                url_for(
                    "main.report_request",
                    service_id=service_id,
                    report_request_id=report_request_id,
                )
            )
        else:
            raise e

    if report_request.user_id != current_user.id:
        abort(403)
    # if they bookmarked the page and come back to it
    # show them either the error for failed or no reports available page
    if report_request.status != REPORT_REQUEST_STORED:
        return redirect(
            url_for(
                "main.report_request",
                service_id=service_id,
                report_request_id=report_request_id,
            )
        )

    return render_template(
        "views/csv-report/ready.html",
        retention_period=current_service.get_days_of_retention(report_request.parameter["notification_type"]),
        report_request=report_request,
    )


@main.route("/services/<uuid:service_id>/report-request/<uuid:report_request_id>.csv")
@user_has_permissions("view_activity")
def report_request_download(service_id, report_request_id):
    validate_report_request_enabled()

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


# this endpoint is used by Javascript to poll for changes every N seconds
@main.route("/services/<uuid:service_id>/download-report/<uuid:report_request_id>/status.json")
@user_has_permissions("view_activity")
def report_request_status_json(service_id, report_request_id):
    validate_report_request_enabled()

    report_request_status = ReportRequest.from_id(service_id, report_request_id).status
    return jsonify({"status": report_request_status})

from flask import jsonify, render_template, url_for
from notifications_python_client.errors import HTTPError
from werkzeug.utils import redirect

from app import current_service
from app.constants import REPORT_REQUEST_FAILED, REPORT_REQUEST_STORED
from app.main import main
from app.models.report_request import ReportRequest
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/download-report/<uuid:report_request_id>", methods=["GET"])
@user_has_permissions()
def csv_report_request(service_id, report_request_id):
  # if users have bookmarked the page and they come back to it, there will likely be no report available
  try:
    report_request = ReportRequest.from_id(service_id, report_request_id)
  except HTTPError as e:
      if e.status_code == 404:
        report_request = None
        report_status = None
        notification_type = None
        notification_status = None
        page_title= "Your report is no longer available"
  else:
    report_status = report_request.status
    # if they refresh that page manually before JS does
    # or they copy and paste that url in manually or bookmark it
    # we redirect them to the download page
    if report_status == REPORT_REQUEST_STORED:
       return redirect(
        url_for(
            "main.csv_report_ready",
            service_id=current_service.id,
            report_request_id=report_request_id,
        )
      )
    else:
      notification_type =  report_request.parameter['notification_type']
      notification_status =  report_request.parameter['notification_status']
      page_title = "Error: We could not create your report" \
        if report_status == REPORT_REQUEST_FAILED else "Preparing your report"


  return render_template(
      "views/csv-report/index.html",
      retention_period = current_service.get_days_of_retention('email'),
      notification_status = notification_status,
      notification_type = notification_type,
      report_status = report_status,
      page_title = page_title,
      report_request = report_request,
      report_request_id = report_request_id,
  )

@main.route("/services/<uuid:service_id>/download-report/<uuid:report_request_id>/ready", methods=["GET"])
@user_has_permissions()
def csv_report_ready(service_id, report_request_id):
  try:
    report_request = ReportRequest.from_id(service_id, report_request_id)
  except HTTPError as e:
      if e.status_code == 404:
         # if the report is no longer available, show them "No longer available page"
        return redirect(
          url_for(
              "main.csv_report_request",
              service_id=current_service.id,
              report_request_id=report_request_id,
              report_request = None,
              report_status = None,
              notification_type = None,
              notification_status = None,
          )
        )
  else:
    # if they bookmarked the page and come back to it
    # show them either the error for failed or no reports available page
    if report_request.status != REPORT_REQUEST_STORED:
      return redirect(
        url_for(
            "main.csv_report_request",
            service_id=current_service.id,
            report_request_id=report_request_id,
        )
      )
    else:
      return render_template(
        "views/csv-report/ready.html",
        retention_period = current_service.get_days_of_retention('email'),
        notification_status = report_request.parameter['notification_status'],
        notification_type = report_request.parameter['notification_type'],
        report_request_id = report_request_id,
      )

@main.route("/services/<uuid:service_id>/download-report/<uuid:report_request_id>/status.json")
@user_has_permissions()
def report_request_status_updates(service_id, report_request_id):
  report_request_status = ReportRequest.from_id(service_id, report_request_id).status
  return jsonify({
    "status": report_request_status
  })

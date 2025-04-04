from flask import render_template, request

from app import current_service, report_request_api_client
from app.main import main
from app.utils.user import user_has_permissions
from notifications_python_client.errors import HTTPError

@main.route("/services/<uuid:service_id>/download-report/<uuid:request_id>", methods=["GET"])
@user_has_permissions()
def csv_report_request(service_id, request_id):
  # if users have bookmarked the page and they com back to it, there will likely be no report avaialble
  # get report status
  try:
    report_request = report_request_api_client.get_report_request(service_id, request_id).get("data", {})
  except HTTPError as e:
      if e.status_code == 404:
        report_request = None
        report_status = None
        notification_type = None
        notification_status = None
        page_title= "Your report is no longer available"
  else:
    report_request = report_request_api_client.get_report_request(service_id, request_id).get("data", {})
    report_status = report_request['status']
    notification_type =  report_request['parameter']['notification_type']
    notification_status =  report_request['parameter']['notification_status']
    page_title= "Error: We could not create your report" if report_status == 'failed' else "Preparing your report"


  return render_template(
      "views/csv-report/index.html",
      retention_period = current_service.get_days_of_retention('email'),
      notification_status = notification_status,
      notification_type = notification_type,
      report_status = report_status,
      page_title = page_title,
      report_request = report_request,
  )
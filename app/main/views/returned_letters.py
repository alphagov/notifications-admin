from flask import render_template, request

from app import service_api_client
from app.main import main
from app.utils import user_has_permissions


@main.route("/services/<uuid:service_id>/returned-letter-summary", methods=["GET", "POST"])
@user_has_permissions('manage_service')
def returned_letter_summary(service_id):
    summary = service_api_client.get_returned_letter_summary(service_id)
    return render_template(
        'views/returned-letter-summary.html',
        data=summary,
    )


@main.route("/services/<uuid:service_id>/returned-letters-csv/<reported_at>", methods=["GET", "POST"])
@user_has_permissions('manage_service')
def returned_letters_report(service_id, reported_at):

    return str(service_api_client.get_returned_letters(service_id, reported_at))

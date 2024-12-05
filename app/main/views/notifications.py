import base64
import io
import json
import os
from datetime import datetime

from flask import (
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from notifications_python_client.errors import APIError, HTTPError
from notifications_utils.pdf import pdf_page_count
from pypdf.errors import PdfReadError

from app import (
    current_service,
    format_date_numeric,
    notification_api_client,
    template_preview_client,
)
from app.main import json_updates, main
from app.models.notification import Notification
from app.utils import (
    NOTIFICATION_TYPES,
    get_help_argument,
    parse_filter_args,
    set_status_filters,
)
from app.utils.csv import generate_notifications_csv
from app.utils.letters import get_letter_validation_error
from app.utils.templates import get_template
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/notification/<uuid:notification_id>")
@user_has_permissions("view_activity", "send_messages")
def view_notification(service_id, notification_id):
    notification = Notification.from_id_and_service_id(str(notification_id), service_id)

    error_message = None
    page_count = None

    if notification.is_precompiled_letter:
        try:
            file_contents, metadata = get_letter_file_data(service_id, notification_id, "pdf", with_metadata=True)
            page_count = (
                int(metadata["page_count"]) if metadata.get("page_count") else pdf_page_count(io.BytesIO(file_contents))
            )
            if notification.status == "validation-failed":
                invalid_pages = metadata.get("invalid_pages")
                invalid_pages = json.loads(invalid_pages) if invalid_pages else invalid_pages
                error_message = get_letter_validation_error(metadata.get("message"), invalid_pages, page_count)
        except PdfReadError:
            return render_template(
                "views/notifications/invalid_precompiled_letter.html", created_at=notification.created_at
            )

    template = get_template(
        notification.template,
        current_service,
        letter_preview_url=url_for(
            ".view_letter_notification_as_preview",
            service_id=service_id,
            notification_id=notification_id,
            filetype="png",
        ),
        page_count=page_count,
        show_recipient=True,
        redact_missing_personalisation=True,
        sms_sender=notification.reply_to_text,
        email_reply_to=notification.reply_to_text,
    )
    template.values = notification.personalisation
    template.postage = notification.displayed_postage

    if template.template_type == "letter" and template.too_many_pages:
        # We check page count here to show the right error message for a letter that is too long.
        # Another way to do this would be to get the status and error message from letter metadata.
        # This would be a significant amount of work though, out of scope for this bug fix.
        # This is because currently we do not pull the letter from S3 when showing preview.
        # Instead, we generate letter preview based on the letter template and personalisation.
        # Additionally, when a templated letter is sent via the api and the personalisation pushes the
        # page count over 10 pages, it takes a while for validation status to come through.
        # Checking page count here will enable us to show the error message even if the letter is not
        # fully processed yet.
        error_message = get_letter_validation_error("letter-too-long", [1], template.page_count)

    if get_help_argument() or request.args.get("help") == "0":
        # help=0 is set when you’ve just sent a notification. We
        # only want to show the back link when you’ve navigated to a
        # notification, not when you’ve just sent it.
        back_link = None
    elif request.args.get("from_job"):
        back_link = url_for(
            "main.view_job",
            service_id=current_service.id,
            job_id=request.args.get("from_job"),
        )
    elif request.args.get("from_uploaded_letters"):
        back_link = url_for(
            "main.uploaded_letters",
            service_id=current_service.id,
            letter_print_day=request.args.get("from_uploaded_letters"),
        )
    else:
        back_link = url_for(
            "main.view_notifications",
            service_id=current_service.id,
            message_type=template.template_type,
            status=request.args.get("from_statuses", "sending,delivered,failed"),
            search_query=request.args.get("from_search_query", None),
        )

    return render_template(
        "views/notifications/notification.html",
        notification=notification,
        message=error_message,
        template=template,
        updates_url=url_for(
            "json_updates.view_notification_updates",
            service_id=service_id,
            notification_id=notification.id,
            status=request.args.get("status"),
            help=get_help_argument(),
        ),
        partials=get_single_notification_partials(notification),
        help=get_help_argument(),
        back_link=back_link,
    )


@main.route("/services/<uuid:service_id>/notification/<uuid:notification_id>/cancel", methods=["GET", "POST"])
@user_has_permissions("view_activity", "send_messages")
def cancel_letter(service_id, notification_id):
    if request.method == "POST":
        try:
            notification_api_client.update_notification_to_cancelled(current_service.id, notification_id)
        except HTTPError as e:
            message_fragments = ["already been cancelled", "too late to cancel"]
            if e.status_code == 400 and any(fragment in e.message for fragment in message_fragments):
                flash(e.message)
            else:
                raise e
        return redirect(url_for("main.view_notification", service_id=service_id, notification_id=notification_id))

    flash("Are you sure you want to cancel sending this letter?", "cancel")
    return view_notification(service_id, notification_id)


def get_preview_error_image():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "static", "images", "preview_error.png")
    with open(path, "rb") as file:
        return file.read()


@main.route("/services/<uuid:service_id>/notification/<uuid:notification_id>.<letter_file_extension:filetype>")
@user_has_permissions("view_activity", "send_messages")
def view_letter_notification_as_preview(service_id, notification_id, filetype, with_metadata=False):
    notification = Notification.from_id_and_service_id(notification_id, service_id)
    if not notification.is_precompiled_letter:
        return template_preview_client.get_preview_for_templated_letter(
            db_template=notification.template,
            filetype=filetype,
            values=notification.personalisation,
            page=request.args.get("page"),
            service=current_service,
        )

    image_data = get_letter_file_data(service_id, notification_id, filetype, with_metadata)
    file = io.BytesIO(image_data)

    mimetype = "image/png" if filetype == "png" else "application/pdf"

    return send_file(
        path_or_file=file,
        mimetype=mimetype,
    )


def get_letter_file_data(service_id, notification_id, filetype, with_metadata=False):
    try:
        preview = notification_api_client.get_notification_letter_preview(
            service_id, notification_id, filetype, page=request.args.get("page")
        )

        display_file = base64.b64decode(preview["content"])
    except APIError:
        display_file = get_preview_error_image()
        preview = {"metadata": {}}

    if with_metadata:
        return display_file, preview["metadata"]
    return display_file


@json_updates.route("/services/<uuid:service_id>/notification/<uuid:notification_id>.json")
@user_has_permissions("view_activity", "send_messages")
def view_notification_updates(service_id, notification_id):
    return jsonify(**get_single_notification_partials(Notification.from_id_and_service_id(notification_id, service_id)))


def get_single_notification_partials(notification):
    return {
        "status": render_template(
            "partials/notifications/status.html",
            notification=notification,
        ),
    }


@main.route("/services/<uuid:service_id>/download-notifications.csv")
@user_has_permissions("view_activity")
def download_notifications_csv(service_id):
    filter_args = parse_filter_args(request.args)
    filter_args["status"] = set_status_filters(filter_args)

    if (
        "message_type" not in filter_args
        or (message_type := filter_args.get("message_type")[0]) not in NOTIFICATION_TYPES
    ):
        abort(404)

    service_data_retention_days = current_service.get_days_of_retention(message_type)

    data = generate_notifications_csv(
        service_id=service_id,
        status=filter_args.get("status"),
        page=request.args.get("page", 1),
        page_size=10000,
        template_type=message_type,
        limit_days=service_data_retention_days,
    )
    return Response(
        list(data),
        mimetype="text/csv",
        headers={
            "Content-Disposition": 'inline; filename="{} - {} - {} report.csv"'.format(
                format_date_numeric(datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")),
                message_type,
                current_service.name,
            ),
        },
    )

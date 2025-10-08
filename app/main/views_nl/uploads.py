import base64
import itertools
import json
import uuid
from datetime import datetime
from functools import partial
from io import BytesIO
from zipfile import BadZipFile

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from notifications_utils.insensitive_dict import InsensitiveDict
from notifications_utils.pdf import pdf_page_count
from notifications_utils.recipient_validation.postal_address import PostalAddress
from notifications_utils.recipients import RecipientCSV
from notifications_utils.sanitise_text import SanitiseASCII
from pypdf.errors import PdfReadError
from requests import RequestException
from xlrd.biffh import XLRDError
from xlrd.xldate import XLDateError

from app import (
    current_service,
    notification_api_client,
    template_preview_client,
    upload_api_client,
)
from app.main import main
from app.main.forms import CsvUploadForm, LetterUploadPostageForm, PDFUploadForm
from app.models.contact_list import ContactList
from app.s3_client.s3_letter_upload_client import (
    LetterNotFoundError,
    backup_original_letter_to_s3,
    get_letter_metadata,
    get_letter_pdf_and_metadata,
    get_transient_letter_file_location,
    upload_letter_to_s3,
)
from app.utils import unicode_truncate
from app.utils.csv import Spreadsheet, get_errors_for_csv
from app.utils.letters import (
    get_letter_printing_statement,
    get_letter_validation_error,
)
from app.utils.pagination import (
    generate_next_dict,
    generate_previous_dict,
    get_page_from_request,
)
from app.utils.templates import get_sample_template
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/uploads")
@user_has_permissions()
def uploads(service_id):
    # No tests have been written, this has been quickly prepared for user research.
    # It's also very like that a new view will be created to show uploads.
    uploads = current_service.get_page_of_uploads(page=request.args.get("page"))

    prev_page = None
    if uploads.prev_page:
        prev_page = generate_previous_dict("main.uploads", service_id, uploads.current_page)
    next_page = None
    if uploads.next_page:
        next_page = generate_next_dict("main.uploads", service_id, uploads.current_page)

    if uploads.current_page == 1:
        listed_uploads = current_service.contact_lists + current_service.scheduled_jobs + uploads
    else:
        listed_uploads = uploads

    return render_template(
        "views/jobs/jobs.html",
        jobs=listed_uploads,
        prev_page=prev_page,
        next_page=next_page,
        now=datetime.utcnow().isoformat(),
    )


@main.route("/services/<uuid:service_id>/uploaded-letters/<simple_date:letter_print_day>")
@user_has_permissions()
def uploaded_letters(service_id, letter_print_day):
    page = get_page_from_request()
    if page is None:
        abort(404, f"Invalid page argument ({request.args.get('page')}).")
    uploaded_letters = upload_api_client.get_letters_by_service_and_print_day(
        current_service.id,
        letter_print_day=letter_print_day,
        page=page,
    )

    prev_page = None
    if uploaded_letters["links"].get("prev"):
        prev_page = generate_previous_dict(
            ".uploaded_letters", service_id, page, url_args={"letter_print_day": letter_print_day}
        )
    next_page = None
    if uploaded_letters["links"].get("next"):
        next_page = generate_next_dict(
            ".uploaded_letters", service_id, page, url_args={"letter_print_day": letter_print_day}
        )
    return render_template(
        "views/uploads/uploaded-letters.html",
        notifications=add_preview_of_content_uploaded_letters(uploaded_letters["notifications"]),
        prev_page=prev_page,
        next_page=next_page,
        show_pagination=True,
        total=uploaded_letters["total"],
        letter_printing_statement=get_letter_printing_statement(
            "created",
            letter_print_day,
        ),
        letter_print_day=letter_print_day,
        single_notification_url=partial(
            url_for,
            "main.view_notification",
            service_id=current_service.id,
            from_uploaded_letters=letter_print_day,
        ),
        limit_days=None,
    )


def add_preview_of_content_uploaded_letters(notifications):
    for notification in notifications:
        yield dict(
            preview_of_content=", ".join(notification.pop("to").splitlines()),
            to=notification["client_reference"],
            **notification,
        )


@main.route("/services/<uuid:service_id>/upload-letter", methods=["GET", "POST"])
@user_has_permissions("send_messages")
def upload_letter(service_id):
    form = PDFUploadForm()

    if form.validate_on_submit():
        pdf_file_bytes = form.file.data.read()

        try:
            # TODO: get page count from the sanitise response once template preview handles malformed files nicely
            page_count = pdf_page_count(BytesIO(pdf_file_bytes))
        except PdfReadError:
            current_app.logger.info("Invalid PDF uploaded for service_id: %s", service_id)
            form.file.errors.append("Notify cannot read this PDF - save a new copy and try again")

        if not form.errors:
            original_filename = form.file.data.filename
            upload_id = uuid.uuid4()
            file_location = get_transient_letter_file_location(service_id, upload_id)

            try:
                response = template_preview_client.sanitise_letter(
                    BytesIO(pdf_file_bytes),
                    upload_id=upload_id,
                    allow_international_letters=current_service.has_permission("international_letters"),
                )
                response.raise_for_status()
            except RequestException as ex:
                if ex.response is not None and ex.response.status_code == 400:
                    validation_failed_message = response.json().get("message")
                    invalid_pages = response.json().get("invalid_pages")

                    status = "invalid"
                    upload_letter_to_s3(
                        pdf_file_bytes,
                        file_location=file_location,
                        status=status,
                        page_count=page_count,
                        filename=original_filename,
                        message=validation_failed_message,
                        invalid_pages=invalid_pages,
                    )
                else:
                    raise ex
            else:
                response = response.json()
                recipient = response["recipient_address"]
                status = "valid"
                file_contents = base64.b64decode(response["file"].encode())

                upload_letter_to_s3(
                    file_contents,
                    file_location=file_location,
                    status=status,
                    page_count=page_count,
                    filename=original_filename,
                    recipient=recipient,
                )

                backup_original_letter_to_s3(
                    pdf_file_bytes,
                    upload_id=upload_id,
                )

            return redirect(
                url_for(
                    "main.uploaded_letter_preview",
                    service_id=current_service.id,
                    file_id=upload_id,
                )
            )

    return render_template("views/uploads/upload-letter.html", form=form, error_summary_enabled=True), (
        400 if form.errors else 200
    )


@main.route("/services/<uuid:service_id>/preview-letter/<uuid:file_id>")
@user_has_permissions("send_messages")
def uploaded_letter_preview(service_id, file_id):
    re_upload_form = PDFUploadForm()

    try:
        metadata = get_letter_metadata(service_id, file_id)
    except LetterNotFoundError:
        current_app.logger.warning("Uploaded letter preview failed", exc_info=True)

        # If the file is missing it's likely because this is a duplicate
        # request, the notification already exists and the file has been
        # moved to a different bucket. Note that the ID of a precompiled
        # notification is always set to the file_id.
        return redirect(
            url_for(
                "main.view_notification",
                service_id=service_id,
                notification_id=file_id,
            )
        )

    original_filename = metadata.get("filename")
    page_count = int(metadata.get("page_count"))
    status = metadata.get("status")
    error_shortcode = metadata.get("message")
    invalid_pages = metadata.get("invalid_pages")
    postal_address = PostalAddress(metadata.get("recipient", ""))

    if invalid_pages:
        invalid_pages = json.loads(invalid_pages)

    error_message = get_letter_validation_error(error_shortcode, invalid_pages, page_count)

    form = LetterUploadPostageForm(postage_zone=postal_address.postage)

    template = current_service.get_precompiled_letter_template(
        letter_preview_url=url_for(".view_letter_upload_as_preview", service_id=service_id, file_id=file_id),
        page_count=page_count,
    )

    return render_template(
        "views/uploads/preview.html",
        original_filename=original_filename,
        template=template,
        status=status,
        file_id=file_id,
        message=error_message,
        error_code=error_shortcode,
        form=form,
        allowed_file_extensions=Spreadsheet.ALLOWED_FILE_EXTENSIONS,
        postal_address=postal_address,
        re_upload_form=re_upload_form,
    )


@main.route("/services/<uuid:service_id>/preview-letter-image/<uuid:file_id>")
@user_has_permissions("send_messages")
def view_letter_upload_as_preview(service_id, file_id):
    try:
        page = int(request.args.get("page"))
    except ValueError:
        abort(400)

    pdf_file, metadata = get_letter_pdf_and_metadata(service_id, file_id)
    invalid_pages = json.loads(metadata.get("invalid_pages", "[]"))

    if metadata.get("message") == "content-outside-printable-area" and page in invalid_pages:
        return template_preview_client.get_png_for_invalid_pdf_page(pdf_file, page)
    else:
        return template_preview_client.get_png_for_valid_pdf_page(pdf_file, page)


@main.route("/services/<uuid:service_id>/upload-letter/send/<uuid:file_id>", methods=["POST"])
@user_has_permissions("send_messages", restrict_admin_usage=True)
def send_uploaded_letter(service_id, file_id):
    if not current_service.has_permission("letter"):
        abort(403)

    try:
        metadata = get_letter_metadata(service_id, file_id)
    except LetterNotFoundError:
        current_app.logger.warning("Get letter metadata failed", exc_info=True)

        # If the file is missing it's likely because this is a duplicate
        # request, the notification already exists and the file has been
        # moved to a different bucket. Note that the ID of a precompiled
        # notification is always set to the file_id.
        return redirect(
            url_for(
                "main.view_notification",
                service_id=service_id,
                notification_id=file_id,
            )
        )

    if metadata.get("status") != "valid":
        abort(403)

    postal_address = PostalAddress(metadata.get("recipient"))

    form = LetterUploadPostageForm(postage_zone=postal_address.postage)

    if not form.validate_on_submit():
        return uploaded_letter_preview(service_id, file_id)

    notification_api_client.send_precompiled_letter(
        service_id,
        metadata.get("filename"),
        file_id,
        form.postage.data,
        postal_address.raw_address,
    )

    return redirect(
        url_for(
            "main.view_notification",
            service_id=service_id,
            notification_id=file_id,
        )
    )


@main.route("/services/<uuid:service_id>/upload-contact-list", methods=["GET", "POST"])
@user_has_permissions("send_messages")
def upload_contact_list(service_id):
    form = CsvUploadForm()

    if form.validate_on_submit():
        try:
            upload_id = ContactList.upload(
                current_service.id,
                Spreadsheet.from_file_form(form).as_dict,
            )
            file_name_metadata = unicode_truncate(SanitiseASCII.encode(form.file.data.filename), 1600)
            ContactList.set_metadata(current_service.id, upload_id, original_file_name=file_name_metadata)
            return redirect(
                url_for(
                    ".check_contact_list",
                    service_id=service_id,
                    upload_id=upload_id,
                )
            )
        except (UnicodeDecodeError, BadZipFile, XLRDError):
            form.file.errors = ["Notify cannot read this file - try using a different file type"]
        except XLDateError:
            form.file.errors = ["Notify cannot read this file - try saving it as a CSV instead"]
    elif form.errors:
        # just show the first error, as we don't expect the form to have more
        # than one, since it only has one field
        first_field_errors = list(form.errors.values())[0]
        form.file.errors.append(first_field_errors[0])

    return render_template(
        "views/uploads/contact-list/upload.html",
        form=form,
        allowed_file_extensions=Spreadsheet.ALLOWED_FILE_EXTENSIONS,
        error_summary_enabled=True,
    )


@main.route(
    "/services/<uuid:service_id>/check-contact-list/<uuid:upload_id>",
    methods=["GET", "POST"],
)
@user_has_permissions("send_messages")
def check_contact_list(service_id, upload_id):
    form = CsvUploadForm()

    contents = ContactList.download(service_id, upload_id)
    first_row = contents.splitlines()[0].strip().rstrip(",") if contents else ""
    original_file_name = ContactList.get_metadata(service_id, upload_id).get("original_file_name", "")

    template_type = InsensitiveDict(
        {
            "email address": "email",
            "phone number": "sms",
        }
    ).get(first_row)

    recipients = RecipientCSV(
        contents,
        template=get_sample_template(template_type or "sms"),
        guestlist=(
            itertools.chain.from_iterable(
                [user.name, user.mobile_number, user.email_address] for user in current_service.active_users
            )
            if current_service.trial_mode
            else None
        ),
        allow_international_sms=current_service.has_permission("international_sms"),
        max_initial_rows_shown=50,
        max_errors_shown=50,
    )

    non_empty_column_headers = list(filter(None, recipients.column_headers))

    if len(non_empty_column_headers) > 1 or not template_type or not recipients:
        return render_template(
            "views/uploads/contact-list/too-many-columns.html",
            recipients=recipients,
            original_file_name=original_file_name,
            template_type=template_type,
            form=form,
            allowed_file_extensions=Spreadsheet.ALLOWED_FILE_EXTENSIONS,
        )

    if recipients.too_many_rows or not len(recipients):
        return render_template(
            "views/uploads/contact-list/column-errors.html",
            recipients=recipients,
            original_file_name=original_file_name,
            form=form,
            allowed_file_extensions=Spreadsheet.ALLOWED_FILE_EXTENSIONS,
        )

    if row_errors := get_errors_for_csv(recipients, template_type):
        return render_template(
            "views/uploads/contact-list/row-errors.html",
            recipients=recipients,
            original_file_name=original_file_name,
            row_errors=row_errors,
            form=form,
            allowed_file_extensions=Spreadsheet.ALLOWED_FILE_EXTENSIONS,
        )

    if recipients.has_errors:
        return render_template(
            "views/uploads/contact-list/column-errors.html",
            recipients=recipients,
            original_file_name=original_file_name,
            form=form,
            allowed_file_extensions=Spreadsheet.ALLOWED_FILE_EXTENSIONS,
        )

    metadata_kwargs = {
        "row_count": len(recipients),
        "valid": True,
        "original_file_name": original_file_name,
        "template_type": template_type,
    }

    ContactList.set_metadata(service_id, upload_id, **metadata_kwargs)

    return render_template(
        "views/uploads/contact-list/ok.html",
        recipients=recipients,
        original_file_name=original_file_name,
        upload_id=upload_id,
    )


@main.route("/services/<uuid:service_id>/save-contact-list/<uuid:upload_id>", methods=["POST"])
@user_has_permissions("send_messages")
def save_contact_list(service_id, upload_id):
    ContactList.create(current_service.id, upload_id)
    return redirect(
        url_for(
            ".uploads",
            service_id=current_service.id,
        )
    )


@main.route("/services/<uuid:service_id>/contact-list/<uuid:contact_list_id>", methods=["GET"])
@user_has_permissions("send_messages")
def contact_list(service_id, contact_list_id):
    contact_list = ContactList.from_id(contact_list_id, service_id=service_id)
    return render_template(
        "views/uploads/contact-list/contact-list.html",
        contact_list=contact_list,
        jobs=contact_list.get_jobs(
            page=1,
            limit_days=current_service.get_days_of_retention(contact_list.template_type),
        ),
    )


@main.route("/services/<uuid:service_id>/contact-list/<uuid:contact_list_id>/delete", methods=["GET", "POST"])
@user_has_permissions("manage_templates")
def delete_contact_list(service_id, contact_list_id):
    contact_list = ContactList.from_id(contact_list_id, service_id=service_id)

    if request.method == "POST":
        contact_list.delete()
        return redirect(
            url_for(
                ".uploads",
                service_id=service_id,
            )
        )

    flash(
        [
            f"Are you sure you want to delete ‘{contact_list.original_file_name}’?",
        ],
        "delete",
    )

    return render_template(
        "views/uploads/contact-list/contact-list.html",
        contact_list=contact_list,
        confirm_delete_banner=True,
    )


@main.route("/services/<uuid:service_id>/contact-list/<uuid:contact_list_id>.csv", methods=["GET"])
@user_has_permissions("send_messages")
def download_contact_list(service_id, contact_list_id):
    contact_list = ContactList.from_id(contact_list_id, service_id=service_id)
    return send_file(
        path_or_file=BytesIO(contact_list.contents.encode("utf-8")),
        download_name=contact_list.saved_file_name,
        as_attachment=True,
    )

import io

from flask import redirect, render_template, request, send_file, url_for
from notifications_utils.base64_uuid import uuid_to_base64

from app import current_service, current_user
from app.main import main
from app.main.forms import DocumentDownloadConfirmEmailAddressForm
from app.url_converters import base64_to_uuid_or_404
from app.utils import assess_contact_type
from app.utils.user import user_has_permissions


@main.route("/d/<base64_uuid:service_id>/<base64_uuid:document_id>")
@user_has_permissions()
def document_download_index(service_id, document_id):
    template_id = base64_to_uuid_or_404(request.args.get("key"))
    template = current_service.get_template_with_user_permission_or_403(
        template_id,
        current_user,
        must_be_of_type="email",
    )
    template_email_file = template.email_files.by_id(document_id)

    return render_template(
        "views/document-download/index.html",
        template=template,
        next_page=url_for(
            "main.document_download_confirm_email_address",
            service_id=current_service.id,
            document_id=template_email_file.id,
            key=uuid_to_base64(template.id),
        ),
    )


@main.route("/d/<base64_uuid:service_id>/<base64_uuid:document_id>/confirm-email-address", methods=["GET", "POST"])
@user_has_permissions()
def document_download_confirm_email_address(service_id, document_id):
    template_id = base64_to_uuid_or_404(request.args.get("key"))
    template = current_service.get_template_with_user_permission_or_403(
        template_id,
        current_user,
        must_be_of_type="email",
    )
    template_email_file = template.email_files.by_id(document_id)

    form = DocumentDownloadConfirmEmailAddressForm(
        current_user_email_address=current_user.email_address,
        service_name=current_service.name,
    )

    if not template_email_file.validate_users_email or form.validate_on_submit():
        return redirect(
            url_for(
                "main.document_download_page",
                service_id=current_service.id,
                document_id=template_email_file.id,
                key=uuid_to_base64(template.id),
            )
        )

    return render_template(
        "views/document-download/confirm-email-address.html",
        form=form,
        template=template,
    )


@main.route("/d/<base64_uuid:service_id>/<base64_uuid:document_id>/download", methods=["GET"])
@user_has_permissions()
def document_download_page(service_id, document_id):
    template_id = base64_to_uuid_or_404(request.args.get("key"))
    template = current_service.get_template_with_user_permission_or_403(
        template_id,
        current_user,
        must_be_of_type="email",
    )
    template_email_file = template.email_files.by_id(document_id)

    # If the download link has been activated, the file content is then retrieved
    if request.args.get("download") and request.args.get("mimetype"):
        data = template_email_file.get_file_content_for_download()
        mimetype = request.args.get("mimetype")
        return send_file(
            io.BytesIO(data), mimetype=mimetype, as_attachment=True, download_name=template_email_file.filename
        )
    s3_file_metadata = template_email_file.get_file_metadata()
    service_contact_info = current_service.contact_link
    contact_info_type = assess_contact_type(current_service.contact_link)
    return render_template(
        "views/document-download/download.html",
        template=template,
        download_link=url_for(
            "main.document_download_page",
            service_id=current_service.id,
            document_id=template_email_file.id,
            key=uuid_to_base64(template.id),
            download=True,
            mimetype=s3_file_metadata["mimetype"],
        ),
        file_size=s3_file_metadata["file_size"],
        file_type=s3_file_metadata["file_type"],
        mimetype=s3_file_metadata["mimetype"],
        service_name=current_service.name,
        service_contact_info=service_contact_info,
        contact_info_type=contact_info_type,
    )

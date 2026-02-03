from flask import redirect, render_template, request, url_for
from notifications_utils.base64_uuid import uuid_to_base64

from app import current_service, current_user
from app.main import main
from app.main.forms import DocumentDownloadConfirmEmailAddressForm
from app.url_converters import base64_to_uuid_or_404
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
        return redirect("https://www.example.com")

    return render_template(
        "views/document-download/confirm-email-address.html",
        form=form,
    )

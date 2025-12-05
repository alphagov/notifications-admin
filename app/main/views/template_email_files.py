import uuid

from flask import redirect, render_template, url_for

from app import current_service, current_user, template_email_file_client
from app.main import main
from app.main.forms import TemplateEmailFilesUploadForm
from app.s3_client.s3_template_email_file_upload_client import upload_template_email_file_to_s3
from app.utils import service_has_permission
from app.utils.user import user_has_permissions


def _get_file_location_from_upload_id(file_id, service_id, template_id):
    return f"service-{service_id}/template-{template_id}/{file_id}"


@main.route("/services/<uuid:service_id>/templates/<uuid:template_id>/files/upload", methods=["GET", "POST"])
@service_has_permission("send_files_via_ui")
@user_has_permissions("manage_templates")
def email_template_files_upload(template_id, service_id):
    template = current_service.get_template_with_user_permission_or_403(
        template_id,
        current_user,
        must_be_of_type="email",
    )
    form = TemplateEmailFilesUploadForm()
    if form.validate_on_submit():
        file_id = uuid.uuid4()
        filename = form.file.data.filename
        file_bytes = form.file.data.read()
        file_location = _get_file_location_from_upload_id(file_id, service_id, template_id)
        upload_template_email_file_to_s3(data=file_bytes, file_location=file_location)
        template_email_file_client.create_file(file_id, service_id, template_id, filename, current_user.id)
        return redirect(
            url_for(
                "main.view_template",
                service_id=service_id,
                template_id=template_id,
            )
        )

    return render_template(
        "views/templates/email-template-files/upload.html",
        template=template,
        form=form,
    )

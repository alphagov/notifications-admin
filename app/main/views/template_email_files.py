from flask import redirect, render_template, url_for
from notifications_utils.insensitive_dict import InsensitiveSet

from app import current_service, current_user, service_api_client
from app.main import main
from app.main.forms import TemplateEmailFilesUploadForm
from app.models.template_email_file import TemplateEmailFile
from app.utils import service_has_permission
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/templates/<uuid:template_id>/files/upload", methods=["GET", "POST"])
@service_has_permission("send_files_via_ui")
@user_has_permissions("manage_templates")
def upload_template_email_files(template_id, service_id):
    template = current_service.get_template_with_user_permission_or_403(
        template_id,
        current_user,
        must_be_of_type="email",
    )
    form = TemplateEmailFilesUploadForm(existing_files=template.email_files)
    if form.validate_on_submit():
        TemplateEmailFile.create(
            filename=form.file.data.filename,
            file_contents=form.file.data,
            template_id=template.id,
        )

        if form.file.data.filename not in InsensitiveSet(template.placeholders):
            new_content = template.content + f"\n\n(({form.file.data.filename}))"
            service_api_client.update_service_template(
                service_id=service_id,
                template_id=template_id,
                content=new_content,
            )

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

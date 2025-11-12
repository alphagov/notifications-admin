from flask import render_template

from app import current_service, current_user
from app.main import main
from app.main.forms import TemplateEmailFilesUploadForm
from app.utils import service_has_permission
from app.utils.user import user_has_permissions


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
        pass
    return render_template(
        "views/templates/email-template-files/upload.html",
        template=template,
        form=form,
    )

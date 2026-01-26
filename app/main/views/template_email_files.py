from flask import abort, redirect, render_template, url_for
from notifications_utils.insensitive_dict import InsensitiveSet

from app import current_service, current_user, service_api_client
from app.main import main
from app.main.forms import TemplateEmailFileLinkTextForm, TemplateEmailFilesUploadForm
from app.models.template_email_file import TemplateEmailFile
from app.utils import service_has_permission
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/templates/<uuid:template_id>/files", methods=["GET"])
@service_has_permission("send_files_via_ui")
@user_has_permissions("manage_templates")
def template_email_files(template_id, service_id):
    template = current_service.get_template_with_user_permission_or_403(
        template_id,
        current_user,
        must_be_of_type="email",
    )
    return render_template(
        "views/templates/email-template-files/files-list.html", template=template, data=template.email_files
    )


@main.route(
    "/services/<uuid:service_id>/templates/<uuid:template_id>/files/<uuid:template_email_file_id>", methods=["GET"]
)
@service_has_permission("send_files_via_ui")
@user_has_permissions("manage_templates")
def manage_a_template_email_file(service_id, template_id, template_email_file_id):
    template = current_service.get_template_with_user_permission_or_403(
        template_id,
        current_user,
        must_be_of_type="email",
    )

    if email_file_data := template.get_email_file_data(template_email_file_id):
        return render_template(
            "views/templates/email-template-files/email_file.html",
            email_file_data=email_file_data,
            template_id=template_id,
            template_email_file_id=template_email_file_id,
        )
    else:
        raise abort(404, f"Invalid template_email_file_id: {template_email_file_id}")


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


@main.route(
    "/services/<uuid:service_id>/templates/<uuid:template_id>/files/<uuid:template_email_file_id>/change_link_text",
    methods=["GET", "POST"],
)
@service_has_permission("send_files_via_ui")
@user_has_permissions("manage_templates")
def change_link_text(service_id, template_id, template_email_file_id):
    template = current_service.get_template_with_user_permission_or_403(
        template_id,
        current_user,
        must_be_of_type="email",
    )
    email_file_data = template.get_email_file_data(template_email_file_id)
    form = TemplateEmailFileLinkTextForm(link_text=email_file_data["link_text"])

    if form.validate_on_submit():
        email_file_data["link_text"] = form.link_text.data
        TemplateEmailFile.update(template_email_file_id, template_id, data=email_file_data)
        return redirect(
            url_for(
                "main.manage_a_template_email_file",
                service_id=service_id,
                template_id=template_id,
                template_email_file_id=template_email_file_id,
            )
        )

    return render_template(
        "views/templates/email-template-files/change_link_text.html",
        template=template,
        form=form,
        template_email_file_id=template_email_file_id,
    )

from flask import render_template, request

from app import current_service, current_user
from app.main import main
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
    template.email_files.by_id(document_id)

    return render_template("views/document-download/index.html")

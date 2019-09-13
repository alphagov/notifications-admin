import base64
import uuid
from io import BytesIO

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from notifications_utils.pdf import pdf_page_count
from PyPDF2.utils import PdfReadError
from requests import RequestException

from app import current_service, notification_api_client, service_api_client
from app.extensions import antivirus_client
from app.main import main
from app.main.forms import PDFUploadForm
from app.s3_client.s3_letter_upload_client import (
    get_letter_pdf_and_metadata,
    get_transient_letter_file_location,
    upload_letter_to_s3,
)
from app.template_previews import TemplatePreview, sanitise_letter
from app.utils import get_template, user_has_permissions

MAX_FILE_UPLOAD_SIZE = 2 * 1024 * 1024  # 2MB


@main.route("/services/<service_id>/uploads")
@user_has_permissions('send_messages')
def uploads(service_id):
    return render_template('views/uploads/index.html')


@main.route("/services/<service_id>/upload-letter", methods=['GET', 'POST'])
@user_has_permissions('send_messages')
def upload_letter(service_id):
    form = PDFUploadForm()

    if form.validate_on_submit():
        pdf_file_bytes = form.file.data.read()

        virus_free = antivirus_client.scan(BytesIO(pdf_file_bytes))
        if not virus_free:
            return invalid_upload_error('Your file has failed the virus check')

        if len(pdf_file_bytes) > MAX_FILE_UPLOAD_SIZE:
            return invalid_upload_error('Your file must be smaller than 2MB')

        try:
            # TODO: get page count from the sanitise response once template preview handles malformed files nicely
            page_count = pdf_page_count(BytesIO(pdf_file_bytes))
        except PdfReadError:
            current_app.logger.info('Invalid PDF uploaded for service_id: {}'.format(service_id))
            return invalid_upload_error('Your file must be a valid PDF')

        upload_id = uuid.uuid4()
        file_location = get_transient_letter_file_location(service_id, upload_id)

        try:
            response = sanitise_letter(BytesIO(pdf_file_bytes))
            response.raise_for_status()
        except RequestException as ex:
            if ex.response is not None and ex.response.status_code == 400:
                status = 'invalid'
                upload_letter_to_s3(pdf_file_bytes, file_location, status)
            else:
                raise ex
        else:
            status = 'valid'
            file_contents = base64.b64decode(response.json()['file'].encode())
            upload_letter_to_s3(file_contents, file_location, status)

        return redirect(
            url_for(
                'main.uploaded_letter_preview',
                service_id=current_service.id,
                file_id=upload_id,
                original_filename=form.file.data.filename,
                page_count=page_count,
                status=status,
            )
        )

    return render_template('views/uploads/choose-file.html', form=form)


def invalid_upload_error(message):
    flash(message, 'dangerous')
    return render_template('views/uploads/choose-file.html', form=PDFUploadForm()), 400


@main.route("/services/<service_id>/preview-letter/<file_id>")
@user_has_permissions('send_messages')
def uploaded_letter_preview(service_id, file_id):
    original_filename = request.args.get('original_filename')
    page_count = request.args.get('page_count')
    status = request.args.get('status')

    template_dict = service_api_client.get_precompiled_template(service_id)

    template = get_template(
        template_dict,
        service_id,
        letter_preview_url=url_for(
            '.view_letter_upload_as_preview',
            service_id=service_id,
            file_id=file_id
        ),
        page_count=page_count
    )

    return render_template(
        'views/uploads/preview.html',
        original_filename=original_filename,
        template=template,
        status=status,
        file_id=file_id,
    )


@main.route("/services/<service_id>/preview-letter-image/<file_id>")
@user_has_permissions('send_messages')
def view_letter_upload_as_preview(service_id, file_id):
    file_location = get_transient_letter_file_location(service_id, file_id)
    pdf_file, metadata = get_letter_pdf_and_metadata(file_location)

    page = request.args.get('page')

    if metadata['status'] == 'invalid':
        return TemplatePreview.from_invalid_pdf_file(pdf_file, page)
    else:
        return TemplatePreview.from_valid_pdf_file(pdf_file, page)


@main.route("/services/<service_id>/upload-letter/send", methods=['POST'])
@user_has_permissions('send_messages', restrict_admin_usage=True)
def send_uploaded_letter(service_id):
    filename = request.form['filename']
    file_id = request.form['file_id']

    if not (current_service.has_permission('letter') and current_service.has_permission('upload_letters')):
        abort(403)

    file_location = get_transient_letter_file_location(service_id, file_id)
    _, metadata = get_letter_pdf_and_metadata(file_location)

    if metadata.get('status') != 'valid':
        abort(403)

    notification_api_client.send_precompiled_letter(service_id, filename, file_id)

    return redirect(url_for(
        '.view_notification',
        service_id=service_id,
        notification_id=file_id,
    ))

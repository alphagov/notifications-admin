import base64
import itertools
import json
import urllib
import uuid
from io import BytesIO
from zipfile import BadZipFile

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from notifications_utils.columns import Columns
from notifications_utils.pdf import pdf_page_count
from notifications_utils.recipients import RecipientCSV
from notifications_utils.sanitise_text import SanitiseASCII
from PyPDF2.utils import PdfReadError
from requests import RequestException
from xlrd.biffh import XLRDError
from xlrd.xldate import XLDateError

from app import current_service, notification_api_client, service_api_client
from app.extensions import antivirus_client
from app.main import main
from app.main.forms import CsvUploadForm, LetterUploadPostageForm, PDFUploadForm
from app.models.contact_list import ContactList
from app.s3_client.s3_letter_upload_client import (
    get_letter_metadata,
    get_letter_pdf_and_metadata,
    get_transient_letter_file_location,
    upload_letter_to_s3,
)
from app.template_previews import TemplatePreview, sanitise_letter
from app.utils import (
    Spreadsheet,
    generate_next_dict,
    generate_previous_dict,
    get_errors_for_csv,
    get_letter_validation_error,
    get_template,
    unicode_truncate,
    user_has_permissions,
)

MAX_FILE_UPLOAD_SIZE = 2 * 1024 * 1024  # 2MB


@main.route("/services/<uuid:service_id>/uploads")
@user_has_permissions()
def uploads(service_id):
    # No tests have been written, this has been quickly prepared for user research.
    # It's also very like that a new view will be created to show uploads.
    uploads = current_service.get_page_of_uploads(page=request.args.get('page'))

    prev_page = None
    if uploads.prev_page:
        prev_page = generate_previous_dict('main.uploads', service_id, uploads.current_page)
    next_page = None
    if uploads.next_page:
        next_page = generate_next_dict('main.uploads', service_id, uploads.current_page)

    if uploads.current_page == 1:
        listed_uploads = current_service.scheduled_jobs + uploads
    else:
        listed_uploads = uploads

    return render_template(
        'views/jobs/jobs.html',
        jobs=listed_uploads,
        prev_page=prev_page,
        next_page=next_page,
    )


@main.route("/services/<uuid:service_id>/upload-letter", methods=['GET', 'POST'])
@user_has_permissions('send_messages')
def upload_letter(service_id):
    form = PDFUploadForm()
    error = {}

    if form.validate_on_submit():
        pdf_file_bytes = form.file.data.read()
        original_filename = form.file.data.filename

        if current_app.config['ANTIVIRUS_ENABLED']:
            virus_free = antivirus_client.scan(BytesIO(pdf_file_bytes))
            if not virus_free:
                return invalid_upload_error('Your file contains a virus')

        if len(pdf_file_bytes) > MAX_FILE_UPLOAD_SIZE:
            return invalid_upload_error('Your file is too big', 'Files must be smaller than 2MB.')

        try:
            # TODO: get page count from the sanitise response once template preview handles malformed files nicely
            page_count = pdf_page_count(BytesIO(pdf_file_bytes))
        except PdfReadError:
            current_app.logger.info('Invalid PDF uploaded for service_id: {}'.format(service_id))
            return invalid_upload_error(
                "There’s a problem with your file",
                'Notify cannot read this PDF.<br>Save a new copy of your file and try again.'
            )

        upload_id = uuid.uuid4()
        file_location = get_transient_letter_file_location(service_id, upload_id)

        try:
            response = sanitise_letter(BytesIO(pdf_file_bytes))
            response.raise_for_status()
        except RequestException as ex:
            if ex.response is not None and ex.response.status_code == 400:
                validation_failed_message = response.json().get('message')
                invalid_pages = response.json().get('invalid_pages')

                status = 'invalid'
                upload_letter_to_s3(
                    pdf_file_bytes,
                    file_location=file_location,
                    status=status,
                    page_count=page_count,
                    filename=original_filename,
                    message=validation_failed_message,
                    invalid_pages=invalid_pages)
            else:
                raise ex
        else:
            response = response.json()
            recipient = response['recipient_address']
            status = 'valid'
            file_contents = base64.b64decode(response['file'].encode())

            upload_letter_to_s3(
                file_contents,
                file_location=file_location,
                status=status,
                page_count=page_count,
                filename=original_filename,
                recipient=recipient)

        return redirect(
            url_for(
                'main.uploaded_letter_preview',
                service_id=current_service.id,
                file_id=upload_id,
            )
        )

    if form.file.errors:
        error = _get_error_from_upload_form(form.file.errors[0])

    return render_template(
        'views/uploads/choose-file.html',
        error=error,
        form=form
    )


def invalid_upload_error(error_title, error_detail=None):
    return render_template(
        'views/uploads/choose-file.html',
        error={'title': error_title, 'detail': error_detail},
        form=PDFUploadForm()
    ), 400


def _get_error_from_upload_form(form_errors):
    error = {}
    if 'PDF' in form_errors:
        error['title'] = 'Wrong file type'
        error['detail'] = form_errors
    else:  # No file was uploaded error
        error['title'] = form_errors

    return error


def format_recipient(address):
    '''
    To format the recipient we need to:
        - decode, address is url encoded
        - remove new line characters
        - remove whitespace around the lines
        - join the address lines, separated by a comma
    '''
    if not address:
        return address
    address = urllib.parse.unquote(address)
    stripped_address_lines_no_trailing_commas = [
        line.lstrip().rstrip(' ,')
        for line in address.splitlines() if line
    ]
    one_line_address = ', '.join(stripped_address_lines_no_trailing_commas)
    return one_line_address


@main.route("/services/<uuid:service_id>/preview-letter/<uuid:file_id>")
@user_has_permissions('send_messages')
def uploaded_letter_preview(service_id, file_id):
    re_upload_form = PDFUploadForm()

    metadata = get_letter_metadata(service_id, file_id)
    original_filename = metadata.get('filename')
    page_count = metadata.get('page_count')
    status = metadata.get('status')
    error_shortcode = metadata.get('message')
    invalid_pages = metadata.get('invalid_pages')
    recipient = format_recipient(metadata.get('recipient', ''))

    if invalid_pages:
        invalid_pages = json.loads(invalid_pages)

    error_message = get_letter_validation_error(error_shortcode, invalid_pages, page_count)
    template_dict = service_api_client.get_precompiled_template(service_id)
    # Override pre compiled letter template postage to none as it has not yet been picked even though
    # the pre compiled letter template has its postage set as second class as the DB currently requires
    # a non null value of postage for letter templates
    template_dict['postage'] = None

    form = LetterUploadPostageForm()

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
        message=error_message,
        error_code=error_shortcode,
        form=form,
        recipient=recipient,
        re_upload_form=re_upload_form
    )


@main.route("/services/<uuid:service_id>/preview-letter-image/<uuid:file_id>")
@user_has_permissions('send_messages')
def view_letter_upload_as_preview(service_id, file_id):
    try:
        page = int(request.args.get('page'))
    except ValueError:
        abort(400)

    pdf_file, metadata = get_letter_pdf_and_metadata(service_id, file_id)
    invalid_pages = json.loads(metadata.get('invalid_pages', '[]'))

    if (
        metadata.get('message') == 'content-outside-printable-area' and
        page in invalid_pages
    ):
        return TemplatePreview.from_invalid_pdf_file(pdf_file, page)
    else:
        return TemplatePreview.from_valid_pdf_file(pdf_file, page)


@main.route("/services/<uuid:service_id>/upload-letter/send", methods=['POST'])
@user_has_permissions('send_messages', restrict_admin_usage=True)
def send_uploaded_letter(service_id):
    if not (current_service.has_permission('letter') and current_service.has_permission('upload_letters')):
        abort(403)

    form = LetterUploadPostageForm()
    file_id = form.file_id.data

    if not form.validate_on_submit():
        return uploaded_letter_preview(service_id, file_id)

    postage = form.postage.data
    metadata = get_letter_metadata(service_id, file_id)
    filename = metadata.get('filename')
    recipient_address = metadata.get('recipient')

    if metadata.get('status') != 'valid':
        abort(403)

    notification_api_client.send_precompiled_letter(service_id, filename, file_id, postage, recipient_address)

    return redirect(url_for(
        '.view_notification',
        service_id=service_id,
        notification_id=file_id,
    ))


@main.route("/services/<uuid:service_id>/upload-contact-list", methods=['GET', 'POST'])
@user_has_permissions('send_messages')
def upload_contact_list(service_id):
    form = CsvUploadForm()

    if form.validate_on_submit():
        try:
            upload_id = ContactList.upload(
                current_service.id,
                Spreadsheet.from_file_form(form).as_dict,
            )
            return redirect(url_for(
                '.check_contact_list',
                service_id=service_id,
                upload_id=upload_id,
                original_file_name=form.file.data.filename,
            ))
        except (UnicodeDecodeError, BadZipFile, XLRDError):
            flash('Could not read {}. Try using a different file format.'.format(
                form.file.data.filename
            ))
        except (XLDateError):
            flash((
                '{} contains numbers or dates that Notify cannot understand. '
                'Try formatting all columns as ‘text’ or export your file as CSV.'
            ).format(
                form.file.data.filename
            ))

    return render_template(
        'views/uploads/contact-list/upload.html',
        form=form,
    )


@main.route(
    "/services/<uuid:service_id>/check-contact-list/<uuid:upload_id>",
    methods=['GET', 'POST'],
)
@user_has_permissions('send_messages')
def check_contact_list(service_id, upload_id):

    form = CsvUploadForm()

    contents = ContactList.download(service_id, upload_id)
    first_row = contents.splitlines()[0].strip().rstrip(',') if contents else ''

    template_type = {
        'emailaddress': 'email',
        'phonenumber': 'sms',
    }.get(Columns.make_key(first_row))

    original_file_name = SanitiseASCII.encode(request.args.get('original_file_name', ''))

    recipients = RecipientCSV(
        contents,
        template_type=template_type or 'sms',
        whitelist=itertools.chain.from_iterable(
            [user.name, user.mobile_number, user.email_address]
            for user in current_service.active_users
        ) if current_service.trial_mode else None,
        international_sms=current_service.has_permission('international_sms'),
        max_initial_rows_shown=50,
        max_errors_shown=50,
    )

    non_empty_column_headers = list(filter(None, recipients.column_headers))

    if len(non_empty_column_headers) > 1 or not template_type or not recipients:
        return render_template(
            'views/uploads/contact-list/too-many-columns.html',
            recipients=recipients,
            original_file_name=original_file_name,
            template_type=template_type,
            form=form,
        )

    if recipients.too_many_rows or not len(recipients):
        return render_template(
            'views/uploads/contact-list/column-errors.html',
            recipients=recipients,
            original_file_name=original_file_name,
            form=form,
        )

    row_errors = get_errors_for_csv(recipients, template_type)
    if row_errors:
        return render_template(
            'views/uploads/contact-list/row-errors.html',
            recipients=recipients,
            original_file_name=original_file_name,
            row_errors=row_errors,
            form=form,
        )

    if recipients.has_errors:
        return render_template(
            'views/uploads/contact-list/column-errors.html',
            recipients=recipients,
            original_file_name=original_file_name,
            form=form,
        )

    metadata_kwargs = {
        'row_count': len(recipients),
        'valid': True,
        'original_file_name': unicode_truncate(
            original_file_name,
            1600,
        ),
        'template_type': template_type
    }

    ContactList.set_metadata(service_id, upload_id, **metadata_kwargs)

    return render_template(
        'views/uploads/contact-list/ok.html',
        recipients=recipients,
        original_file_name=original_file_name,
        upload_id=upload_id,
    )


@main.route("/services/<uuid:service_id>/save-contact-list/<uuid:upload_id>", methods=['POST'])
@user_has_permissions('send_messages')
def save_contact_list(service_id, upload_id):
    ContactList.create(current_service.id, upload_id)
    return redirect(url_for(
        '.contact_list',
        service_id=current_service.id,
        contact_list_id=upload_id,
    ))


@main.route("/services/<uuid:service_id>/contact-list/<uuid:contact_list_id>", methods=['GET'])
@user_has_permissions('send_messages')
def contact_list(service_id, contact_list_id):
    return render_template(
        'views/uploads/contact-list/contact-list.html',
        contact_list=ContactList.from_id(contact_list_id, service_id=service_id),
    )

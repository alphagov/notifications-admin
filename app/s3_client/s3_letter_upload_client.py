import json

from boto3 import resource
from flask import current_app
from notifications_utils.s3 import s3upload as utils_s3upload
from notifications_utils.sanitise_text import SanitiseASCII


def get_transient_letter_file_location(service_id, upload_id):
    return 'service-{}/{}.pdf'.format(service_id, upload_id)


def upload_letter_to_s3(
    data,
    *,
    file_location,
    status,
    page_count,
    filename,
    message=None,
    invalid_pages=None,
    recipient=None
):
    metadata = {
        'status': status,
        'page_count': str(page_count),
        'filename': filename,
    }
    if message:
        metadata['message'] = message
    if invalid_pages:
        metadata['invalid_pages'] = json.dumps(invalid_pages)
    if recipient:
        metadata['recipient'] = format_recipient(recipient)

    utils_s3upload(
        filedata=data,
        region=current_app.config['AWS_REGION'],
        bucket_name=current_app.config['TRANSIENT_UPLOADED_LETTERS'],
        file_location=file_location,
        metadata=metadata,
    )


def get_letter_pdf_and_metadata(service_id, file_id):
    file_location = get_transient_letter_file_location(service_id, file_id)
    s3 = resource('s3')
    s3_object = s3.Object(current_app.config['TRANSIENT_UPLOADED_LETTERS'], file_location).get()

    pdf = s3_object['Body'].read()
    metadata = s3_object['Metadata']

    return pdf, metadata


def get_letter_metadata(service_id, file_id):
    file_location = get_transient_letter_file_location(service_id, file_id)
    s3 = resource('s3')
    s3_object = s3.Object(current_app.config['TRANSIENT_UPLOADED_LETTERS'], file_location).get()

    return s3_object['Metadata']


def format_recipient(address):
    '''
    To format the recipient we need to:
    - remove new line characters
    - remove whitespace around the lines
    - join the address lines, separated by a comma
    - convert the string to ASCII (S3 metadata must be stored as ASCII)
    '''
    stripped_address_lines_no_trailing_commas = [
        line.lstrip().rstrip(' ,')
        for line in address.splitlines() if line
    ]
    one_line_address = ', '.join(stripped_address_lines_no_trailing_commas)

    return SanitiseASCII.encode(one_line_address)

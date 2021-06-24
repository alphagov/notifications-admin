import json
import urllib

from boto3 import resource
from flask import current_app
from notifications_utils.s3 import s3upload as utils_s3upload


def get_transient_letter_file_location(service_id, upload_id):
    return 'service-{}/{}.pdf'.format(service_id, upload_id)


def backup_original_letter_to_s3(
    data,
    upload_id,
):
    utils_s3upload(
        filedata=data,
        region=current_app.config['AWS_REGION'],
        bucket_name=current_app.config['PRECOMPILED_ORIGINALS_BACKUP_LETTERS'],
        file_location=f'{upload_id}.pdf',
    )


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
    # Use of urllib.parse.quote encodes metadata into ascii, which is required by s3.
    # Making sure data for displaying to users is decoded is taken care of by LetterMetadata
    metadata = {
        'status': status,
        'page_count': str(page_count),
        'filename': urllib.parse.quote(filename),
    }
    if message:
        metadata['message'] = message
    if invalid_pages:
        metadata['invalid_pages'] = json.dumps(invalid_pages)
    if recipient:
        metadata['recipient'] = urllib.parse.quote(recipient)

    utils_s3upload(
        filedata=data,
        region=current_app.config['AWS_REGION'],
        bucket_name=current_app.config['TRANSIENT_UPLOADED_LETTERS'],
        file_location=file_location,
        metadata=metadata,
    )


class LetterMetadata:
    KEYS_TO_DECODE = ["filename", "recipient"]

    def __init__(self, metadata):
        self._metadata = metadata

    def get(self, key, default=None):
        value = self._metadata.get(key, default)
        if value and key in self.KEYS_TO_DECODE:
            value = urllib.parse.unquote(value)
        return value


def get_letter_pdf_and_metadata(service_id, file_id):
    file_location = get_transient_letter_file_location(service_id, file_id)
    s3 = resource('s3')
    s3_object = s3.Object(current_app.config['TRANSIENT_UPLOADED_LETTERS'], file_location).get()

    pdf = s3_object['Body'].read()

    return pdf, LetterMetadata(s3_object['Metadata'])


def get_letter_metadata(service_id, file_id):
    file_location = get_transient_letter_file_location(service_id, file_id)
    s3 = resource('s3')
    s3_object = s3.Object(current_app.config['TRANSIENT_UPLOADED_LETTERS'], file_location).get()

    return LetterMetadata(s3_object['Metadata'])

import json
import urllib

from boto3 import resource
from flask import current_app
from notifications_utils.s3 import s3upload as utils_s3upload


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
        metadata['recipient'] = urllib.parse.quote(recipient)

    utils_s3upload(
        filedata=data,
        region=current_app.config['AWS_REGION'],
        bucket_name=current_app.config['TRANSIENT_UPLOADED_LETTERS'],
        file_location=file_location,
        metadata=metadata,
    )


def get_bucket_name_and_prefix_for_notification(notification):
    folder = ''
    NOTIFICATION_VALIDATION_FAILED = 'validation-failed'
    PRECOMPILED_BUCKET_PREFIX = '{folder}NOTIFY.{reference}'
    INVALID_PDF_BUCKET_NAME = 'development-letters-invalid-pdf'

    if notification["status"] == NOTIFICATION_VALIDATION_FAILED:
        bucket_name = 'development-letters-invalid-pdf'
    elif notification["key_type"] == KEY_TYPE_TEST:
        bucket_name = current_app.config['TEST_LETTERS_BUCKET_NAME']
    else:
        bucket_name = current_app.config['LETTERS_PDF_BUCKET_NAME']
        folder = get_folder_name(notification["created_at"], dont_use_sending_date=False)

    upload_file_name = PRECOMPILED_BUCKET_PREFIX.format(
        folder=folder,
        reference=notification["reference"]
    ).upper()

    return bucket_name, upload_file_name


# def get_letter_pdf_and_metadata(service_id, file_id):
#     file_location = get_transient_letter_file_location(service_id, file_id)
#     s3 = resource('s3')
#     s3_object = s3.Object(current_app.config['TRANSIENT_UPLOADED_LETTERS'], file_location).get()

#     pdf = s3_object['Body'].read()
#     metadata = s3_object['Metadata']

#     return pdf, metadata

def get_letter_pdf_and_metadata(notification):
    bucket_name, prefix = get_bucket_name_and_prefix_for_notification(notification)

    s3 = resource('s3')
    bucket = s3.Bucket(bucket_name)
    item = next(x for x in bucket.objects.filter(Prefix=prefix))

    obj = s3.Object(
        bucket_name=bucket_name,
        key=item.key
    ).get()
    return obj["Body"].read(), obj["Metadata"]


def get_letter_metadata(service_id, file_id):
    file_location = get_transient_letter_file_location(service_id, file_id)
    s3 = resource('s3')
    s3_object = s3.Object(current_app.config['TRANSIENT_UPLOADED_LETTERS'], file_location).get()

    return s3_object['Metadata']

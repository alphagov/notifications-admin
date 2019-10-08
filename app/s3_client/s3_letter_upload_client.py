from boto3 import resource
from flask import current_app
from notifications_utils.s3 import s3upload as utils_s3upload


def get_transient_letter_file_location(service_id, upload_id):
    return 'service-{}/{}.pdf'.format(service_id, upload_id)


def upload_letter_to_s3(data, *, file_location, status, page_count, filename):
    utils_s3upload(
        filedata=data,
        region=current_app.config['AWS_REGION'],
        bucket_name=current_app.config['TRANSIENT_UPLOADED_LETTERS'],
        file_location=file_location,
        metadata={
            'status': status,
            'page_count': str(page_count),
            'filename': filename,
        }
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

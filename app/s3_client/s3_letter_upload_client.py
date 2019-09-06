from flask import current_app
from notifications_utils.s3 import s3upload as utils_s3upload


def get_transient_letter_file_location(service_id, upload_id):
    return 'service-{}/{}.pdf'.format(service_id, upload_id)


def upload_letter_to_s3(data, file_location, status):
    utils_s3upload(
        filedata=data,
        region=current_app.config['AWS_REGION'],
        bucket_name=current_app.config['TRANSIENT_UPLOADED_LETTERS'],
        file_location=file_location,
        metadata={'status': status}
    )

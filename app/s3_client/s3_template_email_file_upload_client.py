from flask import current_app
from notifications_utils.s3 import s3upload as utils_s3upload


def upload_template_email_file_to_s3(data, file_location):
    metadata = {}

    utils_s3upload(
        filedata=data,
        region=current_app.config["AWS_REGION"],
        bucket_name=current_app.config["S3_BUCKET_DOCUMENT_DOWNLOAD_LONG_TERM_FILE_STORAGE"],
        file_location=file_location,
        metadata=metadata,
    )

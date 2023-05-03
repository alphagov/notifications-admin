import json
import urllib

import botocore
from boto3 import resource
from flask import current_app
from notifications_utils.s3 import s3upload as utils_s3upload


class LetterNotFoundError(Exception):
    pass


def get_transient_letter_file_location(service_id, upload_id):
    return f"service-{service_id}/{upload_id}.pdf"


def backup_original_letter_to_s3(
    data,
    upload_id,
):
    utils_s3upload(
        filedata=data,
        region=current_app.config["AWS_REGION"],
        bucket_name=current_app.config["S3_BUCKET_PRECOMPILED_ORIGINALS_BACKUP_LETTERS"],
        file_location=f"{upload_id}.pdf",
    )


def upload_letter_to_s3(
    data, *, file_location, status, page_count, filename, message=None, invalid_pages=None, recipient=None
):
    # Use of urllib.parse.quote encodes metadata into ascii, which is required by s3.
    # Making sure data for displaying to users is decoded is taken care of by LetterMetadata
    metadata = {
        "status": status,
        "page_count": str(page_count),
        "filename": urllib.parse.quote(filename),
    }
    if message:
        metadata["message"] = message
    if invalid_pages:
        metadata["invalid_pages"] = json.dumps(invalid_pages)
    if recipient:
        metadata["recipient"] = urllib.parse.quote(recipient)

    utils_s3upload(
        filedata=data,
        region=current_app.config["AWS_REGION"],
        bucket_name=current_app.config["S3_BUCKET_TRANSIENT_UPLOADED_LETTERS"],
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


class LetterAttachmentMetadata:
    def __init__(self, metadata):
        self._metadata = metadata

    def get(self, key, default=None):
        value = self._metadata.get(key, default)
        return value


def get_letter_s3_object(service_id, file_id, bucket_name="S3_BUCKET_TRANSIENT_UPLOADED_LETTERS"):
    try:
        file_location = get_transient_letter_file_location(service_id, file_id)
        s3 = resource("s3")
        return s3.Object(current_app.config[bucket_name], file_location).get()
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise LetterNotFoundError(f"Letter not found for service {service_id} and file {file_id}") from e

        raise


def get_letter_pdf_and_metadata(service_id, file_id):
    s3_object = get_letter_s3_object(service_id, file_id)
    pdf = s3_object["Body"].read()
    return pdf, LetterMetadata(s3_object["Metadata"])


def get_letter_metadata(service_id, file_id):
    s3_object = get_letter_s3_object(service_id, file_id)
    return LetterMetadata(s3_object["Metadata"])


def get_attachment_pdf_and_metadata(service_id, file_id):
    s3_object = get_letter_s3_object(service_id, file_id, bucket_name="S3_BUCKET_LETTER_ATTACHMENTS")
    pdf = s3_object["Body"].read()
    return pdf, LetterAttachmentMetadata(s3_object["Metadata"])


def upload_letter_attachment_to_s3(data, *, file_location, page_count, original_filename):
    # Use of urllib.parse.quote encodes metadata into ascii, which is required by s3.
    # Making sure data for displaying to users is decoded is taken care of by LetterMetadata
    metadata = {
        "page_count": str(page_count),
        "filename": urllib.parse.quote(original_filename),
    }
    utils_s3upload(
        filedata=data,
        region=current_app.config["AWS_REGION"],
        bucket_name=current_app.config["S3_BUCKET_LETTER_ATTACHMENTS"],
        file_location=file_location,
        metadata=metadata,
    )

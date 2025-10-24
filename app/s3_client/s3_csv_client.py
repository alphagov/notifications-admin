import uuid

import botocore
from flask import current_app
from notifications_utils.s3 import s3upload as utils_s3upload

from app.s3_client import get_s3_object

FILE_LOCATION_STRUCTURE = "service-{}-notify/{}.csv"


def get_csv_location(service_id, upload_id, bucket=None):
    return (
        bucket or current_app.config["S3_BUCKET_CSV_UPLOAD"],
        FILE_LOCATION_STRUCTURE.format(service_id, upload_id),
    )


def get_csv_upload(service_id, upload_id, bucket=None):
    return get_s3_object(*get_csv_location(service_id, upload_id, bucket))


def s3upload(service_id, filedata, region, bucket=None):
    upload_id = str(uuid.uuid4())
    bucket_name, file_location = get_csv_location(service_id, upload_id, bucket)
    utils_s3upload(
        filedata=filedata["data"],
        region=region,
        bucket_name=bucket_name,
        file_location=file_location,
    )
    return upload_id


def s3download(service_id, upload_id, bucket=None):
    contents = ""
    try:
        key = get_csv_upload(service_id, upload_id, bucket)
        contents = key.get()["Body"].read().decode("utf-8")
    except botocore.exceptions.ClientError as e:
        extra = {
            "upload_id": upload_id,
        }
        extra["s3_key"], extra["s3_bucket"] = get_csv_location(service_id, upload_id, bucket)
        current_app.logger.error("Unable to download s3 file %(s3_key)s from bucket %(s3_bucket)s", extra, extra=extra)
        raise e
    return contents


def set_metadata_on_csv_upload(service_id, upload_id, bucket=None, **kwargs):
    get_csv_upload(service_id, upload_id, bucket=bucket).copy_from(
        CopySource="{}/{}".format(*get_csv_location(service_id, upload_id, bucket=bucket)),
        ServerSideEncryption="AES256",
        Metadata={key: str(value) for key, value in kwargs.items()},
        MetadataDirective="REPLACE",
    )


def get_csv_metadata(service_id, upload_id, bucket=None):
    try:
        key = get_csv_upload(service_id, upload_id, bucket)
        return key.get()["Metadata"]
    except botocore.exceptions.ClientError as e:
        extra = {
            "upload_id": upload_id,
        }
        extra["s3_key"], extra["s3_bucket"] = get_csv_location(service_id, upload_id, bucket)
        current_app.logger.error("Unable to download s3 file %(s3_key)s from bucket %(s3_bucket)s", extra, extra=extra)
        raise e

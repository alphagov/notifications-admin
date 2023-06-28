import botocore
from flask import current_app

from app.s3_client import get_s3_object


def get_mou(organisation_is_crown):
    bucket = current_app.config["S3_BUCKET_MOU"]
    filename = "crown.pdf" if organisation_is_crown else "non-crown.pdf"
    attachment_filename = "GOV.UK Notify data sharing and financial agreement{}.pdf".format(
        "" if organisation_is_crown else " (non-crown)"
    )
    try:
        key = get_s3_object(bucket, filename)
        return {
            "path_or_file": key.get()["Body"],
            "download_name": attachment_filename,
            "as_attachment": True,
        }
    except botocore.exceptions.ClientError as exception:
        current_app.logger.error(
            "Unable to download s3 file %(bucket)s/%(filename)s", dict(bucket=bucket, filename=filename)
        )
        raise exception

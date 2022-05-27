import botocore
from flask import current_app

from app.s3_client.s3_logo_client import get_s3_object


def get_mou(organisation_is_crown):
    bucket = current_app.config['MOU_BUCKET_NAME']
    filename = 'crown.pdf' if organisation_is_crown else 'non-crown.pdf'
    attachment_filename = 'GOV.UK Notify data sharing and financial agreement{}.pdf'.format(
        '' if organisation_is_crown else ' (non-crown)'
    )
    try:
        key = get_s3_object(bucket, filename)
        return {
            'path_or_file': key.get()['Body'],
            'attachment_filename': attachment_filename,
            'as_attachment': True,
        }
    except botocore.exceptions.ClientError as exception:
        current_app.logger.error("Unable to download s3 file {}/{}".format(
            bucket, filename
        ))
        raise exception

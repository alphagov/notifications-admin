import uuid
import botocore
from boto3 import resource
from flask import current_app
from notifications_utils.s3 import s3upload as utils_s3upload

FILE_LOCATION_STRUCTURE = 'service-{}-notify/{}.csv'


def s3upload(service_id, filedata, region):
    upload_id = str(uuid.uuid4())
    upload_file_name = FILE_LOCATION_STRUCTURE.format(service_id, upload_id)
    utils_s3upload(filedata=filedata['data'],
                   region=region,
                   bucket_name=current_app.config['CSV_UPLOAD_BUCKET_NAME'],
                   file_location=upload_file_name)
    return upload_id


def s3download(service_id, upload_id):
    contents = ''
    try:
        s3 = resource('s3')
        bucket_name = current_app.config['CSV_UPLOAD_BUCKET_NAME']
        upload_file_name = FILE_LOCATION_STRUCTURE.format(service_id, upload_id)
        key = s3.Object(bucket_name, upload_file_name)
        contents = key.get()['Body'].read().decode('utf-8')
    except botocore.exceptions.ClientError as e:
        current_app.logger.error("Unable to download s3 file {}".format(
            FILE_LOCATION_STRUCTURE.format(service_id, upload_id)))
        raise e
    return contents

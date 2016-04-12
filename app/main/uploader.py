import botocore
from boto3 import resource
from flask import current_app

FILE_LOCATION_STRUCTURE = 'service-{}-notify/{}.csv'


def s3upload(upload_id, service_id, filedata, region):
    s3 = resource('s3')
    bucket_name = current_app.config['CSV_UPLOAD_BUCKET_NAME']
    contents = filedata['data']

    exists = True
    try:
        s3.meta.client.head_bucket(
            Bucket=bucket_name)
    except botocore.exceptions.ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            exists = False
        else:
            current_app.logger.error(
                "Unable to create s3 bucket {}".format(bucket_name))
            raise e

    if not exists:
        s3.create_bucket(Bucket=bucket_name,
                         CreateBucketConfiguration={'LocationConstraint': region})

    upload_file_name = FILE_LOCATION_STRUCTURE.format(service_id, upload_id)
    key = s3.Object(bucket_name, upload_file_name)
    key.put(Body=contents, ServerSideEncryption='AES256')


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

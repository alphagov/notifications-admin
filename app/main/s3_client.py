import uuid
import botocore
from boto3 import resource, client
from flask import current_app
from notifications_utils.s3 import s3upload as utils_s3upload

FILE_LOCATION_STRUCTURE = 'service-{}-notify/{}.csv'
TEMP_TAG = 'temp-{}_'
LOGO_LOCATION_STRUCTURE = '{}{}-{}'


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


def upload_logo(filename, filedata, region, user_id):
    upload_id = str(uuid.uuid4())
    upload_file_name = LOGO_LOCATION_STRUCTURE.format(TEMP_TAG.format(user_id), upload_id, filename)
    utils_s3upload(filedata=filedata,
                   region=region,
                   bucket_name=current_app.config['LOGO_UPLOAD_BUCKET_NAME'],
                   file_location=upload_file_name,
                   content_type='image/png')
    return upload_file_name


def persist_logo(filename, user_id):
    try:
        if filename.startswith(TEMP_TAG.format(user_id)):
            persisted_filename = filename[len(TEMP_TAG.format(user_id)):]
        else:
            return filename

        s3 = resource('s3')
        bucket_name = current_app.config['LOGO_UPLOAD_BUCKET_NAME']

        s3.Object(bucket_name, persisted_filename).copy_from(CopySource='{}/{}'.format(bucket_name, filename))
        s3.Object(bucket_name, filename).delete()

        return persisted_filename
    except botocore.exceptions.ClientError as e:
        current_app.logger.error("Unable to get s3 bucket contents {}".format(
            bucket_name))
        raise e


def delete_temp_files_created_by(user_id):
    try:
        s3 = resource('s3')
        bucket_name = current_app.config['LOGO_UPLOAD_BUCKET_NAME']

        for obj in s3.Bucket(bucket_name).objects.filter(Prefix=TEMP_TAG.format(user_id)):
            s3.Object(bucket_name, obj.key).delete()

    except botocore.exceptions.ClientError as e:
        current_app.logger.error("Unable to delete s3 bucket temp files created by {} from {}".format(
            user_id, bucket_name))
        raise e


def delete_temp_file(filename):
    try:
        if not filename.startswith(TEMP_TAG):
            raise ValueError('Not a temp file')

        s3 = resource('s3')
        bucket_name = current_app.config['LOGO_UPLOAD_BUCKET_NAME']

        s3.Object(bucket_name, filename).delete()

    except botocore.exceptions.ClientError as e:
        current_app.logger.error("Unable to delete s3 bucket file {} from {}".format(
            filename, bucket_name))
        raise e

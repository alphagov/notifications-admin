import uuid

import botocore
from boto3 import resource
from flask import current_app
from notifications_utils.s3 import s3upload as utils_s3upload

FILE_LOCATION_STRUCTURE = 'service-{}-notify/{}.csv'
TEMP_TAG = 'temp-{user_id}_'
LOGO_LOCATION_STRUCTURE = '{temp}{unique_id}-{filename}'


def get_s3_object(bucket_name, filename):
    s3 = resource('s3')
    return s3.Object(bucket_name, filename)


def get_csv_location(service_id, upload_id):
    return (
        current_app.config['CSV_UPLOAD_BUCKET_NAME'],
        FILE_LOCATION_STRUCTURE.format(service_id, upload_id),
    )


def get_csv_upload(service_id, upload_id):
    return get_s3_object(*get_csv_location(service_id, upload_id))


def delete_s3_object(filename):
    bucket_name = current_app.config['LOGO_UPLOAD_BUCKET_NAME']
    get_s3_object(bucket_name, filename).delete()


def persist_logo(old_name, new_name):
    if old_name == new_name:
        return
    bucket_name = current_app.config['LOGO_UPLOAD_BUCKET_NAME']
    get_s3_object(bucket_name, new_name).copy_from(
        CopySource='{}/{}'.format(bucket_name, old_name))
    delete_s3_object(old_name)


def get_s3_objects_filter_by_prefix(prefix):
    bucket_name = current_app.config['LOGO_UPLOAD_BUCKET_NAME']
    s3 = resource('s3')
    return s3.Bucket(bucket_name).objects.filter(Prefix=prefix)


def get_temp_truncated_filename(filename, user_id):
    return filename[len(TEMP_TAG.format(user_id=user_id)):]


def s3upload(service_id, filedata, region):
    upload_id = str(uuid.uuid4())
    bucket_name, file_location = get_csv_location(service_id, upload_id)
    utils_s3upload(
        filedata=filedata['data'],
        region=region,
        bucket_name=bucket_name,
        file_location=file_location,
    )
    return upload_id


def s3download(service_id, upload_id):
    contents = ''
    try:
        key = get_csv_upload(service_id, upload_id)
        contents = key.get()['Body'].read().decode('utf-8')
    except botocore.exceptions.ClientError as e:
        current_app.logger.error("Unable to download s3 file {}".format(
            FILE_LOCATION_STRUCTURE.format(service_id, upload_id)))
        raise e
    return contents


def get_mou(organisation_is_crown):
    bucket = current_app.config['MOU_BUCKET_NAME']
    filename = 'crown.pdf' if organisation_is_crown else 'non-crown.pdf'
    attachment_filename = 'GOV.UK Notify data sharing and financial agreement{}.pdf'.format(
        '' if organisation_is_crown else ' (non-crown)'
    )
    try:
        key = get_s3_object(bucket, filename)
        return {
            'filename_or_fp': key.get()['Body'],
            'attachment_filename': attachment_filename,
            'as_attachment': True,
        }
    except botocore.exceptions.ClientError as exception:
        current_app.logger.error("Unable to download s3 file {}/{}".format(
            bucket, filename
        ))
        raise exception


def upload_logo(filename, filedata, region, user_id):
    upload_file_name = LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=user_id),
        unique_id=str(uuid.uuid4()),
        filename=filename
    )
    bucket_name = current_app.config['LOGO_UPLOAD_BUCKET_NAME']
    utils_s3upload(
        filedata=filedata,
        region=region,
        bucket_name=bucket_name,
        file_location=upload_file_name,
        content_type='image/png'
    )

    return upload_file_name


def permanent_logo_name(filename, user_id):
    if filename.startswith(TEMP_TAG.format(user_id=user_id)):
        return get_temp_truncated_filename(filename=filename, user_id=user_id)
    else:
        return filename


def delete_temp_files_created_by(user_id):
    for obj in get_s3_objects_filter_by_prefix(TEMP_TAG.format(user_id=user_id)):
        delete_s3_object(obj.key)


def delete_temp_file(filename):
    if not filename.startswith(TEMP_TAG[:5]):
        raise ValueError('Not a temp file: {}'.format(filename))

    delete_s3_object(filename)


def set_metadata_on_csv_upload(service_id, upload_id, **kwargs):
    get_csv_upload(
        service_id, upload_id
    ).copy_from(
        CopySource='{}/{}'.format(*get_csv_location(service_id, upload_id)),
        ServerSideEncryption='AES256',
        Metadata={
            key: str(value) for key, value in kwargs.items()
        },
        MetadataDirective='REPLACE',
    )

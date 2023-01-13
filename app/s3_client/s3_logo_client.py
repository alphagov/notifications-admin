import uuid

from boto3 import client, resource
from flask import current_app
from notifications_utils.s3 import s3upload as utils_s3upload

TEMP_TAG = "temp-{user_id}_"
EMAIL_LOGO_LOCATION_STRUCTURE = "{temp}{unique_id}-{filename}"
LETTER_PREFIX = "letters/static/images/letter-template/"
LETTER_TEMP_TAG = LETTER_PREFIX + TEMP_TAG
LETTER_TEMP_LOGO_LOCATION = "letters/static/images/letter-template/temp-{user_id}_{unique_id}-{filename}"


def get_s3_object(bucket_name, filename):
    s3 = resource("s3")
    return s3.Object(bucket_name, filename)


def delete_s3_object(filename):
    bucket_name = current_app.config["LOGO_UPLOAD_BUCKET_NAME"]
    get_s3_object(bucket_name, filename).delete()


def persist_logo(old_name, new_name):
    if old_name == new_name:
        return
    bucket_name = current_app.config["LOGO_UPLOAD_BUCKET_NAME"]
    get_s3_object(bucket_name, new_name).copy_from(CopySource="{}/{}".format(bucket_name, old_name))
    delete_s3_object(old_name)


def persist_logo_2(logo):
    """
    This removes all tags from a given logo
    """
    s3 = client("s3")
    bucket_name = current_app.config["LOGO_UPLOAD_BUCKET_NAME"]
    return s3.delete_object_tagging(bucket_name, logo)


def get_s3_objects_filter_by_prefix(prefix):
    bucket_name = current_app.config["LOGO_UPLOAD_BUCKET_NAME"]
    s3 = resource("s3")
    return s3.Bucket(bucket_name).objects.filter(Prefix=prefix)


def get_temp_truncated_filename(filename, user_id):
    return filename[len(TEMP_TAG.format(user_id=user_id)) :]


def get_letter_filename_with_no_path_or_extension(filename):
    return filename[len(LETTER_PREFIX) : -4]


def upload_email_logo(filename, filedata, region, user_id, unique_id: str = None):
    if not unique_id:
        unique_id = str(uuid.uuid4())

    upload_file_name = EMAIL_LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=user_id), unique_id=unique_id, filename=filename
    )
    bucket_name = current_app.config["LOGO_UPLOAD_BUCKET_NAME"]
    utils_s3upload(
        filedata=filedata,
        region=region,
        bucket_name=bucket_name,
        file_location=upload_file_name,
        content_type="image/png",
    )

    return upload_file_name


def upload_email_logo_2(filename, filedata):
    bucket_name = current_app.config["LOGO_UPLOAD_BUCKET_NAME"]
    utils_s3upload(
        filedata=filedata,
        region=current_app.config["AWS_REGION"],
        bucket_name=bucket_name,
        file_location=filename,
        tags={"temporary": "true"},
        content_type="image/png",
    )


def upload_letter_temp_logo(filename, filedata, region, user_id, unique_id: str = None):
    if not unique_id:
        unique_id = str(uuid.uuid4())

    upload_filename = LETTER_TEMP_LOGO_LOCATION.format(user_id=user_id, unique_id=unique_id, filename=filename)
    bucket_name = current_app.config["LOGO_UPLOAD_BUCKET_NAME"]
    utils_s3upload(
        filedata=filedata,
        region=region,
        bucket_name=bucket_name,
        file_location=upload_filename,
        content_type="image/svg+xml",
    )

    return upload_filename


def permanent_email_logo_name(filename, user_id):
    if filename.startswith(TEMP_TAG.format(user_id=user_id)):
        return get_temp_truncated_filename(filename=filename, user_id=user_id)
    else:
        return filename


def permanent_letter_logo_name(filename, extension):
    return LETTER_PREFIX + filename + "." + extension


def letter_filename_for_db(filename, user_id):
    filename = get_letter_filename_with_no_path_or_extension(filename)

    if filename.startswith(TEMP_TAG.format(user_id=user_id)):
        filename = get_temp_truncated_filename(filename=filename, user_id=user_id)

    return filename


def delete_email_temp_files_created_by(user_id):
    for obj in get_s3_objects_filter_by_prefix(TEMP_TAG.format(user_id=user_id)):
        delete_s3_object(obj.key)


def delete_letter_temp_files_created_by(user_id):
    for obj in get_s3_objects_filter_by_prefix(LETTER_TEMP_TAG.format(user_id=user_id)):
        delete_s3_object(obj.key)


def delete_email_temp_file(filename):
    if not filename.startswith(TEMP_TAG[:5]):
        raise ValueError("Not a temp file: {}".format(filename))

    delete_s3_object(filename)


def delete_letter_temp_file(filename):
    if not filename.startswith(LETTER_TEMP_TAG[:43]):
        raise ValueError("Not a temp file: {}".format(filename))

    delete_s3_object(filename)

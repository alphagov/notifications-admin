from boto3 import client, resource
from botocore.exceptions import ClientError
from flask import current_app
from notifications_utils.eventlet import EventletTimeout
from notifications_utils.exception_handling import extract_reraise_chained_exception


@extract_reraise_chained_exception(EventletTimeout)
def get_s3_object(bucket_name, filename):
    s3 = resource("s3")
    return s3.Object(bucket_name, filename)


@extract_reraise_chained_exception(EventletTimeout)
def check_s3_object_exists(bucket_name, filename):
    try:
        s3 = client("s3")
        s3.head_object(Bucket=bucket_name, Key=filename)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        else:
            current_app.logger.error(
                "Error when checking file %s in bucket %s",
                filename,
                bucket_name,
                extra={"s3_bucket": bucket_name, "s3_key": filename},
            )
            raise e

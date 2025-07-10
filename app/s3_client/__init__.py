from boto3 import client, resource
from botocore.exceptions import ClientError
from flask import current_app


def get_s3_object(bucket_name, filename):
    s3 = resource("s3")
    return s3.Object(bucket_name, filename)


def check_s3_object_exists(bucket_name, filename):
    try:
        s3 = client("s3")
        s3.head_object(Bucket=bucket_name, Key=filename)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        else:
            current_app.logger.error("Error when checking file %s in bucket %s", filename, bucket_name)
            raise e

from boto3 import resource


def get_s3_object(bucket_name, filename):
    s3 = resource("s3")
    return s3.Object(bucket_name, filename)

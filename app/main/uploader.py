import botocore
from boto3 import resource


def s3upload(upload_id, service_id, filedata, region):
    s3 = resource('s3')
    bucket_name = 'service-{}-notify'.format(service_id)
    contents = '\n'.join(filedata['data'])

    bucket = s3.Bucket(bucket_name)
    exists = True
    try:
        s3.meta.client.head_bucket(Bucket=bucket_name)
    except botocore.exceptions.ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            exists = False

    if not exists:
        s3.create_bucket(Bucket=bucket_name,
                         CreateBucketConfiguration={'LocationConstraint': region})

    key = s3.Object(bucket_name, upload_id)
    key.put(Body=contents, ServerSideEncryption='AES256')


def s3download(service_id, upload_id):
    s3 = resource('s3')
    bucket_name = 'service-{}-notify'.format(service_id)
    key = s3.Object(bucket_name, upload_id)
    contents = key.get()['Body'].read().decode('utf-8')
    return contents

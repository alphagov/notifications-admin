import uuid

from boto3 import resource


def s3upload(service_id, filedata):
    upload_id = str(uuid.uuid4())
    s3 = resource('s3')
    bucket_name = 'service-{}-notify'.format(service_id)
    s3.create_bucket(Bucket=bucket_name)
    contents = '\n'.join(filedata['data'])
    key = s3.Object(bucket_name, upload_id)
    key.put(Body=contents, ServerSideEncryption='AES256')
    return upload_id


def s3download(service_id, upload_id):
    s3 = resource('s3')
    bucket_name = 'service-{}-notify'.format(service_id)
    key = s3.Object(bucket_name, upload_id)
    contents = key.get()['Body'].read().decode('utf-8')
    return contents

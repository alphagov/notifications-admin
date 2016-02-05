import botocore
from boto3 import resource


BUCKET_NAME = 'service-{}-notify'


def s3upload(upload_id, service_id, filedata, region):
    s3 = resource('s3')
    bucket_name = BUCKET_NAME.format(service_id)
    contents = '\n'.join(filedata['data'])

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

    upload_file_name = "{}.csv".format(upload_id)
    key = s3.Object(bucket_name, upload_file_name)
    key.put(Body=contents, ServerSideEncryption='AES256')


def s3download(service_id, upload_id):
    contents = ''
    try:
        s3 = resource('s3')
        bucket_name = BUCKET_NAME.format(service_id)
        upload_file_name = "{}.csv".format(upload_id)
        key = s3.Object(bucket_name, upload_file_name)
        contents = key.get()['Body'].read().decode('utf-8')
    except botocore.exceptions.ClientError as e:
        err = e.response['Error']
        if err['Code'] == 'NoSuchBucket':
            err_msg = '{}:{}'.format(err['BucketName'], err['Message'])
            # TODO properly log error
            print(err_msg)
    return contents

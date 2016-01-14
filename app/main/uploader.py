import os
import uuid

from boto3 import resource


# TODO add service name to bucket name as well
def s3upload(filepath):
    filename = filepath.split(os.path.sep)[-1]
    upload_id = str(uuid.uuid4())
    s3 = resource('s3')
    s3.create_bucket(Bucket=upload_id)
    key = s3.Object(upload_id, filename)
    key.put(Body=open(filepath, 'rb'), ServerSideEncryption='AES256')
    return upload_id

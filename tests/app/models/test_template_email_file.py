from uuid import uuid4

import boto3
from moto import mock_aws

from app.models.template_email_file import TemplateEmailFile, upload_template_email_file_to_s3
from tests.conftest import SERVICE_ONE_ID


@mock_aws
def test_get_metadata_from_uploaded_file(notify_admin, fake_uuid):
    s3 = boto3.client("s3", region_name="eu-west-1")
    s3.create_bucket(Bucket="test-template-email-files", CreateBucketConfiguration={"LocationConstraint": "eu-west-1"})

    upload_template_email_file_to_s3(
        b"hello",
        f"{SERVICE_ONE_ID}/{fake_uuid}",
    )
    template_email_file = TemplateEmailFile(
        {
            "service_id": SERVICE_ONE_ID,
            "template_id": str(uuid4()),
            "id": fake_uuid,
            "filename": "example.pdf",
            "created_by_id": str(uuid4()),
            "retention_period": 78,
            "validate_users_email": True,
        }
    )
    assert template_email_file.size == 5 == len("hello")
    assert template_email_file.file_contents.read() == b"hello"
    assert template_email_file.extension == "pdf"
    assert template_email_file.mimetype == "application/pdf"

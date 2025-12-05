import uuid

from app.s3_client.s3_template_email_file_upload_client import upload_template_email_file_to_s3


def test_upload_template_email_file_to_s3(mocker, notify_admin):
    s3_mock = mocker.patch("app.s3_client.s3_template_email_file_upload_client.utils_s3upload")
    service_id = uuid.uuid4()
    template_id = uuid.uuid4()
    file_id = uuid.uuid4()
    file_location = f"service-{service_id}/template-{template_id}/{file_id}"
    upload_template_email_file_to_s3("file_data", file_location)
    kwargs = {
        "bucket_name": "local-template-email-files",
        "file_location": file_location,
        "filedata": "file_data",
        "metadata": {},
        "region": "eu-west-1",
    }
    s3_mock.assert_called_once_with(**kwargs)

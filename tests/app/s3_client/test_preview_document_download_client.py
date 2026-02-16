import uuid

import pytest
from botocore.stub import Stubber

from app.s3_client.s3_preview_document_download_client import (
    PreviewDocumentDownloadError,
    PreviewDocumentNotFound,
    preview_document_download_client,
)


def test_get_file_metadata_from_s3():
    service_id = uuid.uuid4()
    template_email_file_id = uuid.uuid4()
    filename = f"{service_id}/{template_email_file_id}"
    bucket_name = "test-template-email-files"
    with Stubber(preview_document_download_client.s3_client) as stubber:
        expected_params = {"Bucket": bucket_name, "Key": filename}
        response = {"ContentLength": 1476, "ContentType": "application/pdf"}
        stubber.add_response("head_object", response, expected_params)

        file_metadata = preview_document_download_client.get_file_metadata_from_s3(bucket_name, filename)
        assert file_metadata["ContentLength"] == 1476
        assert file_metadata["ContentType"] == "application/pdf"


def test_get_file_metadata_from_s3_raises_preview_document_download_not_found_error_for_404():
    service_id = uuid.uuid4()
    template_email_file_id = uuid.uuid4()
    filename = f"{service_id}/{template_email_file_id}"
    bucket_name = "test-template-email-files"
    with Stubber(preview_document_download_client.s3_client) as stubber:
        stubber.add_client_error(
            method="head_object",
            service_error_code="404",
            service_message="Not Found.",
            http_status_code=404,
            expected_params={"Bucket": bucket_name, "Key": filename},
        )

        with pytest.raises(PreviewDocumentNotFound) as e:
            preview_document_download_client.get_file_metadata_from_s3(bucket_name, filename)

        assert str(e.value) == "Document Metadata not found"
        error_code = e.value.response["Error"]["Code"]
        error_message = e.value.response["Error"]["Message"]
        operation_name = e.value.operation_name

        assert error_code == "404"
        assert error_message == "Not Found."
        assert operation_name == "HeadObject"


def test_get_file_metadata_from_s3_raises_general_preview_document_download_error_for_all_non_404_errors():
    service_id = uuid.uuid4()
    template_email_file_id = uuid.uuid4()
    filename = f"{service_id}/{template_email_file_id}"
    bucket_name = "test-template-email-files"
    with Stubber(preview_document_download_client.s3_client) as stubber:
        stubber.add_client_error(
            method="head_object",
            service_error_code="403",
            http_status_code=403,
            service_message="Forbidden",
            expected_params={"Bucket": bucket_name, "Key": filename},
        )

        with pytest.raises(PreviewDocumentDownloadError) as e:
            preview_document_download_client.get_file_metadata_from_s3(bucket_name, filename)

        error_code = e.value.response["Error"]["Code"]
        error_message = e.value.response["Error"]["Message"]
        operation_name = e.value.operation_name

        assert error_code == "403"
        assert error_message == "Forbidden"
        assert operation_name == "HeadObject"

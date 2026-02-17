from unittest.mock import MagicMock

import pytest
from botocore.stub import Stubber
from notifications_utils.s3 import S3ObjectNotFound

from app.s3_client.s3_preview_document_download_client import (
    PreviewDocumentDownloadError,
    PreviewDocumentNotFound,
    preview_document_download_client,
)


def test_get_file_metadata_from_s3():
    service_id = "0e30c3dd-7bc1-4d3e-be68-0830549c8b46"
    template_email_file_id = "cdf5d964-c18e-4cab-b12f-6cc65ee4299d"
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
    service_id = "4b983687-93ad-4458-9270-bdac181d655c"
    template_email_file_id = "d23ccc99-f1e7-4971-9c60-666e67af5b08"
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
    service_id = "30ef080c-4690-44a4-9e8d-7934bc03ea8b"
    template_email_file_id = "d78eb935-44d0-4e91-843c-b9cdf1a26fd2"
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
        assert str(e.value) == "Document download error"


def test_get_file_from_s3(mocker):
    service_id = "73ce03de-612b-4172-9924-c3d27bebaed8"
    template_email_file_id = "d2843d7d-97ba-4987-810f-3a05e3b06929"
    filename = f"{service_id}/{template_email_file_id}"
    bucket_name = "test-template-email-files"
    mock_response = MagicMock()
    expected_result = b"file content"
    mock_response.read.return_value = expected_result
    mock_s3_download = mocker.patch(
        "app.s3_client.s3_preview_document_download_client.s3download", return_value=mock_response
    )
    result = preview_document_download_client.get_file_object_body_from_s3(bucket_name, filename)
    assert result.read() == expected_result
    mock_s3_download.assert_called_with("test-template-email-files", f"{service_id}/{template_email_file_id}")


def test_get_file_from_s3_404_error(mocker):
    bucket_name = "test-bucket"
    filename = "test-file"
    error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
    mocker.patch(
        "app.s3_client.s3_preview_document_download_client.s3download",
        side_effect=S3ObjectNotFound(error_response, "GetObject"),
    )
    with pytest.raises(PreviewDocumentNotFound) as e:
        preview_document_download_client.get_file_object_body_from_s3(bucket_name, filename)

    assert e.value.response["Error"]["Code"] == "404"
    assert str(e.value) == "The requested document could not be found"
    assert e.value.operation_name == "GetObject"


def test_get_file_from_s3_raises_general_preview_document_download_error_for_all_non_404_errors(mocker):
    bucket_name = "test-bucket"
    filename = "test-file"
    error_response = {"Error": {"Code": "403", "Message": "Not Found"}}
    mocker.patch(
        "app.s3_client.s3_preview_document_download_client.s3download",
        side_effect=S3ObjectNotFound(error_response, "GetObject"),
    )
    with pytest.raises(PreviewDocumentDownloadError) as e:
        preview_document_download_client.get_file_object_body_from_s3(bucket_name, filename)

    assert e.value.response["Error"]["Code"] == "403"
    assert str(e.value) == "Document download error"
    assert e.value.operation_name == "GetObject"

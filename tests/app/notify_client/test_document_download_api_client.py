import uuid

import pytest
import responses

from app.notify_client.document_download_api_client import DocumentDownloadError, document_download_api_client


def test_document_download_api_file_check(client_request, requests_mock):
    service_id = str(uuid.uuid4())
    client = document_download_api_client
    file_content = b"%PDF-1.4 test content"
    expected_url = f"{client.base_url}/services/{service_id}/antivirus-and-mimetype-check"
    # mock the document download api response
    requests_mock.post(expected_url, json={"mimetype": "application/pdf"}, status_code=201)
    response = client.file_check_and_antivirus_scan(
        service_id=service_id, file_name="example.pdf", file_bytes=file_content
    )
    assert response == {"mimetype": "application/pdf"}


@pytest.mark.parametrize(
    "file_name, error_message, status_code",
    [
        ("example_file", "`filename` must end with a file extension. For example, filename.csv", 400),
        (
            "this_is_a_very_long_filename_that_exceeds_one_hundred_characters_for_testing_validation_boundaries_ok.pdf",
            "`filename` cannot be longer than 100 characters",
            400,
        ),
        (
            "test_file.pdf",
            "The file must be smaller than 2MB",
            413,
        ),
    ],
)
def test_document_download_api_file_check_errors(client_request, requests_mock, file_name, error_message, status_code):
    responses.reset()
    service_id = str(uuid.uuid4())
    client = document_download_api_client
    file_content = b"%PDF-1.4 test content"
    expected_url = f"{client.base_url}/services/{service_id}/antivirus-and-mimetype-check"
    # mock document download api response
    requests_mock.post(expected_url, json={"error": error_message}, status_code=status_code)

    with pytest.raises(DocumentDownloadError) as e:
        client.file_check_and_antivirus_scan(service_id=service_id, file_name=file_name, file_bytes=file_content)

    assert e.value.message == error_message
    assert e.value.status_code == status_code

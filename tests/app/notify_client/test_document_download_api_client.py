import pytest
import uuid
import responses

from app.notify_client.document_download_api_client import document_download_api_client, DocumentDownloadError


def test_document_download_api_file_check(client_request):
    service_id = str(uuid.uuid4())
    client = document_download_api_client
    file_content = b"%PDF-1.4 test content"
    expected_url = f"{client.base_url}/services/{service_id}/antivirus-and-mimetype-check"
    # mock the document download api response
    responses.add(
        responses.POST,
        expected_url,
        json={"mimetype": "application/pdf"},
        status=201
    )
    response = client.file_check(service_id=service_id, file_name="example.pdf", file_bytes=file_content)
    assert response == {"mimetype": "application/pdf"}


@pytest.mark.parametrize(
    "file_name, error_message, status_code", [
        ("example_file", "`filename` must end with a file extension. For example, filename.csv", 400),
        ("this_is_a_very_long_filename_that_exceeds_one_hundred_characters_for_testing_validation_boundaries_ok.pdf",
         "`filename` cannot be longer than 100 characters", 400),
    ]
)
def test_document_download_api_file_check_errors(client_request, file_name, error_message, status_code):
    service_id = str(uuid.uuid4())
    client = document_download_api_client
    file_content = b"%PDF-1.4 test content"
    expected_url = f"{client.base_url}/services/{service_id}/antivirus-and-mimetype-check"
    # mock document download api response
    responses.add(
        responses.POST,
        expected_url,
        json={"error": error_message},
        status=status_code
    )

    with pytest.raises(DocumentDownloadError) as e:
        client.file_check(service_id=service_id, file_name=file_name, file_bytes=file_content)

    assert e.value.message == error_message
    assert e.value.status_code == status_code

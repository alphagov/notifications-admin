from unittest.mock import ANY, Mock, call

import pytest
from notifications_python_client.errors import HTTPError
from notifications_utils.testing.comparisons import AnyStringMatching

from tests import UUID4_REGEX_PATTERN
from tests.conftest import (
    SERVICE_ONE_ID,
    create_template,
    normalize_spaces,
)


@pytest.mark.parametrize(
    "extra_permissions, template_type, expected_status",
    (
        ([], "email", 403),
        ([], "sms", 403),
        ([], "letter", 403),
        (["send_files_via_ui"], "email", 200),
        (["send_files_via_ui"], "sms", 404),
        (["send_files_via_ui"], "letter", 404),
    ),
)
def test_get_upload_file_page(
    client_request,
    service_one,
    fake_uuid,
    extra_permissions,
    template_type,
    expected_status,
    mocker,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type=template_type,
            )
        },
    )
    service_one["permissions"] += extra_permissions
    page = client_request.get(
        "main.email_template_files_upload",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=expected_status,
    )

    if expected_status > 200:
        return

    assert normalize_spaces(page.select_one("h1").text) == "Add a file"

    file_upload_field = page.select_one("form[data-notify-module=file-upload] input[type=file]")
    assert file_upload_field["accept"] == (".csv,.jpeg,.jpg,.png,.xlsx,.doc,.docx,.pdf,.json,.odt,.rtf,.txt")
    assert file_upload_field["data-button-text"] == "Choose file"

    assert [normalize_spaces(li.text) for li in page.select("main ul li")] == [
        "CSV (.csv)",
        "image (.jpeg, .jpg, .png)",
        "Microsoft Excel Spreadsheet (.xlsx)",
        "Microsoft Word Document (.doc, .docx)",
        "PDF (.pdf)",
        "text (.json, .odt, .rtf, .txt)",
    ]


def test_get_upload_file_page_404s_if_invalid_template_id(client_request, service_one, fake_uuid, mocker):
    service_one["permissions"] += ["send_files_via_ui"]
    mocker.patch(
        "app.notify_client.service_api_client.service_api_client.get_service_template",
        side_effect=HTTPError(response=Mock(status_code=404)),
    )
    client_request.get(
        "main.email_template_files_upload",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=404,
    )


def test_upload_file_page_requires_file(
    client_request,
    fake_uuid,
    service_one,
    mock_get_service_email_template,
):
    service_one["permissions"] += ["send_files_via_ui"]
    page = client_request.post(
        "main.email_template_files_upload",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one("form label .govuk-error-message")) == "You need to upload a file to submit"


@pytest.mark.parametrize(
    "test_file, expected_error_message",
    (
        ("tests/test_pdf_files/one_page_pdf.pdf", None),
        ("tests/spreadsheet_files/equivalents/excel 2007.xlsx", None),
        ("tests/spreadsheet_files/equivalents/EXCEL_95.XLS", ".XLS is not an allowed file format"),
        ("tests/test_img_files/small-but-perfectly-formed.png", None),
        ("tests/test_pdf_files/big.pdf", "The file must be smaller than 2MB"),
        ("tests/text_files/without brackets.txt", None),
        ("tests/text_files/with (brackets).txt", "File name cannot contain brackets"),
        ("tests/text_files/no extension", "Not an allowed file format"),
    ),
)
def test_upload_file_page_validates_extentions(
    client_request,
    fake_uuid,
    service_one,
    mock_get_service_email_template,
    test_file,
    expected_error_message,
    mocker,
):
    mock_antivirus = mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    mock_s3 = mocker.patch("app.s3_client.s3_template_email_file_upload_client.utils_s3upload")
    mock_post = mocker.patch("app.template_email_file_client.post")
    mock_template_update = mocker.patch("app.service_api_client.update_service_template")
    service_one["permissions"] += ["send_files_via_ui"]
    if not expected_error_message:
        with open(test_file, "rb") as file:
            page = client_request.post(
                "main.email_template_files_upload",
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
                _data={"file": file},
                _expected_status=302,  # if the form validates we should redirect
            )
        assert mock_s3.called is True
        assert mock_post.called is True
        assert mock_template_update.called is True
    else:
        with open(test_file, "rb") as file:
            page = client_request.post(
                "main.email_template_files_upload",
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
                _data={"file": file},
                _expected_status=200,  # if the form fails to validate we should return upload view with msg
            )

    assert mock_antivirus.called
    error_message = page.select_one("form label .govuk-error-message")

    if expected_error_message:
        assert normalize_spaces(error_message.text) == expected_error_message
    else:
        assert normalize_spaces(page.select_one("h1").text) == "Redirecting..."
        redirect_message = normalize_spaces(page.select_one("p").text)
        assert "You should be redirected automatically to the target URL" in redirect_message
        assert f"/services/{SERVICE_ONE_ID}/templates/{fake_uuid}" in redirect_message
        assert not error_message


def test_file_upload_calls_template_update(
    client_request,
    fake_uuid,
    service_one,
    mocker,
):
    service_one["permissions"] += ["send_files_via_ui"]
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                content="This is a file with a file placeholder",
            )
        },
    )
    mock_antivirus = mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    mock_s3 = mocker.patch("app.s3_client.s3_template_email_file_upload_client.utils_s3upload")
    mock_post = mocker.patch("app.template_email_file_client.post")
    mock_template_update = mocker.patch("app.service_api_client.update_service_template")
    with open("tests/test_pdf_files/one_page_pdf.pdf", "rb") as file:
        client_request.post(
            "main.email_template_files_upload",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _data={"file": file},
            _expected_status=302,
        )
    assert mock_antivirus.called
    mock_template_update.assert_called_once_with(
        template_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        content="This is a file with a file placeholder\n\n((tests/test_pdf_files/one_page_pdf.pdf))",
    )
    assert mock_s3.called
    assert mock_post.called


def test_upload_file_does_not_update_template_when_placeholder_already_exists(
    client_request,
    fake_uuid,
    service_one,
    mocker,
):
    service_one["permissions"] += ["send_files_via_ui"]
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                content="This is a file with a file placeholder ((tests/test_pdf_files/one_page_pdf.pdf))",
            )
        },
    )
    mock_antivirus = mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    mock_s3 = mocker.patch("app.s3_client.s3_template_email_file_upload_client.utils_s3upload")
    mock_post = mocker.patch("app.template_email_file_client.post")
    mock_template_update = mocker.patch("app.service_api_client.update_service_template")
    with open("tests/test_pdf_files/one_page_pdf.pdf", "rb") as file:
        client_request.post(
            "main.email_template_files_upload",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _data={"file": file},
            _expected_status=302,
        )
    assert mock_antivirus.called is True
    assert mock_template_update.call_args_list == []
    assert mock_s3.call_args_list == [
        call(
            filedata=ANY,
            region="eu-west-1",
            bucket_name="local-template-email-files",
            file_location=AnyStringMatching(rf"service-{SERVICE_ONE_ID}/template-{fake_uuid}/{UUID4_REGEX_PATTERN}"),
            metadata={},
        ),
    ]
    assert mock_post.call_args_list == [
        call(
            f"/service/{SERVICE_ONE_ID}/templates/{fake_uuid}/template_email_files",
            data={
                "id": AnyStringMatching(UUID4_REGEX_PATTERN),
                "filename": "tests/test_pdf_files/one_page_pdf.pdf",
                "created_by_id": AnyStringMatching(UUID4_REGEX_PATTERN),
                "retention_period": 90,
                "validate_users_email": False,
            },
        ),
    ]


@pytest.mark.parametrize(
    "existing_filename",
    (
        ("tests/test_pdf_files/one_page_pdf.pdf"),
        ("tests/test_pdf_files/ONE-PAGE PDF.PDF"),
    ),
)
def test_upload_file_returns_error_if_file_with_same_name_exists(
    client_request,
    fake_uuid,
    service_one,
    mocker,
    existing_filename,
):
    service_one["permissions"] += ["send_files_via_ui"]
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                email_files=[
                    {
                        "id": fake_uuid,
                        "filename": existing_filename,
                        "link_text": None,
                        "retention_period": 90,
                        "validate_users_email": False,
                    },
                ],
            )
        },
    )
    mock_antivirus = mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    mock_s3 = mocker.patch("app.s3_client.s3_template_email_file_upload_client.utils_s3upload")
    mock_post = mocker.patch("app.template_email_file_client.post")
    mock_template_update = mocker.patch("app.service_api_client.update_service_template")
    with open("tests/test_pdf_files/one_page_pdf.pdf", "rb") as file:
        page = client_request.post(
            "main.email_template_files_upload",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _data={"file": file},
            _expected_status=200,
        )
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == (
        "Your template already has a file called ‘tests/test_pdf_files/one_page_pdf.pdf’"
    )
    assert mock_antivirus.called is True
    assert mock_template_update.call_args_list == []
    assert mock_s3.call_args_list == []
    assert mock_post.call_args_list == []

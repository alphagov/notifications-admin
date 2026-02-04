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


def test_template_email_files_manage_files_page_displays_the_right_files(
    client_request,
    service_one,
    fake_uuid,
    test_template_email_files_data,
    test_data_for_a_template_email_file,
    mocker,
):
    service_one["permissions"] += ["send_files_via_ui"]
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                email_files=test_template_email_files_data,
            )
        },
    )
    page = client_request.get(
        "main.template_email_files",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    assert page.select_one("h1").string.strip() == "Manage files"
    assert [normalize_spaces(row.text) for row in page.select("dt")] == [
        f"{test_template_email_files_data[0]['filename']}",
        f"{test_template_email_files_data[1]['filename']}",
    ]

    assert (
        normalize_spaces(page.select_one('a[role="button"][data-module="govuk-button"]').get_text())
        == "Attach another file"
    )


def test_template_email_files_manage_files_page_raises_an_error_for_invalid_template_ids(
    client_request,
    service_one,
    fake_uuid,
    mocker,
):
    service_one["permissions"] += ["send_files_via_ui"]
    mocker.patch(
        "app.service_api_client.get_service_template",
        side_effect=HTTPError(response=Mock(status_code=404)),
    )

    client_request.get(
        "main.template_email_files",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=404,
    )


def test_template_email_files_manage_files_page_when_there_are_no_files_to_display(
    client_request,
    service_one,
    fake_uuid,
    mocker,
):
    service_one["permissions"] += ["send_files_via_ui"]

    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
            )
        },
    )
    page = client_request.get(
        "main.template_email_files",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    assert page.select_one("h1").string.strip() == "Manage files"
    assert [normalize_spaces(row.text) for row in page.select("dt")] == [
        "Attached files will show here",
    ]
    assert (
        normalize_spaces(page.select_one('a[role="button"][data-module="govuk-button"]').get_text()) == "Attach files"
    )


def test_manage_a_template_email_file(
    service_one,
    fake_uuid,
    client_request,
    test_template_email_files_data,
    test_data_for_a_template_email_file,
    mocker,
):
    service_one["permissions"] += ["send_files_via_ui"]

    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                email_files=test_template_email_files_data,
            )
        },
    )
    page = client_request.get(
        "main.manage_a_template_email_file",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        template_email_file_id=test_data_for_a_template_email_file["id"],
    )

    assert page.select_one("h1").string.strip() == test_data_for_a_template_email_file["filename"]

    rows = page.select("dl .govuk-summary-list__row:not(.govuk-visually-hidden)")
    assert [normalize_spaces(row.get_text(separator=" ", strip=True)) for row in rows] == [
        "Link text Not set Change",
        "Available for 90 weeks after sending Change",
        "Ask recipient for email address No Change",
    ]


def test_manage_a_template_email_file_raises_404_for_invalid_template_email_file_id(
    service_one,
    fake_uuid,
    client_request,
    mocker,
):
    service_one["permissions"] += ["send_files_via_ui"]
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                email_files=[],
            )
        },
    )
    client_request.get(
        "main.manage_a_template_email_file",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        template_email_file_id="e9ecb3f2-8674-4436-b233-d2c16ad135e7",
        _expected_status=404,
    )


@pytest.mark.parametrize(
    "endpoint, page_title, form_label, path_segment",
    [
        ("main.change_link_text", "Link text", "Link text (optional)", "change_link_text"),
        (
            "main.change_data_retention_period",
            "How long should the file be available for",
            "Number of weeks available to recipients",
            "change_data_retention",
        ),
    ],
)
def test_file_settings_pages_for_link_text_and_retention_period(
    client_request,
    service_one,
    fake_uuid,
    endpoint,
    page_title,
    form_label,
    test_template_email_files_data,
    path_segment,
    mocker,
):
    service_one["permissions"] += ["send_files_via_ui"]
    template_id = fake_uuid
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=template_id,
                template_type="email",
                email_files=test_template_email_files_data,
            )
        },
    )
    template_email_file_id = test_template_email_files_data[0]["id"]
    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        template_id=template_id,
        template_email_file_id=template_email_file_id,
    )
    assert page.select_one("h1").string.strip() == page_title
    assert page.select_one("label").string.strip() == form_label
    form = page.select_one("form[method='post']")
    button = form.select_one(".govuk-button")
    expected_url = f"/services/{SERVICE_ONE_ID}/templates/{fake_uuid}/files/{template_email_file_id}/{path_segment}"
    assert button.text.strip() == "Continue"
    assert form["action"] == expected_url


def test_file_settings_pages_for_email_validation(
    client_request,
    service_one,
    fake_uuid,
    test_template_email_files_data,
    mocker,
):
    service_one["permissions"] += ["send_files_via_ui"]
    template_id = fake_uuid
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=template_id,
                template_type="email",
                email_files=test_template_email_files_data,
            )
        },
    )
    template_email_file_id = test_template_email_files_data[0]["id"]
    page = client_request.get(
        "main.change_email_validation",
        service_id=SERVICE_ONE_ID,
        template_id=template_id,
        template_email_file_id=template_email_file_id,
    )
    assert page.select_one("h1").string.strip() == "Ask recipient for their email address"
    assert [label.text.strip() for label in page.select(".govuk-radios__item label")] == [
        "Yes",
        "No",
    ]

    form = page.select_one("form[method='post']")
    button = form.select_one(".govuk-button")
    expected_url = (
        f"/services/{SERVICE_ONE_ID}/templates/{fake_uuid}/files/{template_email_file_id}/change_email_validation"
    )
    assert button.text.strip() == "Continue"
    assert form["action"] == expected_url


@pytest.mark.parametrize(
    "endpoint, file_setting, updated_value",
    [
        ("main.change_link_text", "link_text", "link text"),
        ("main.change_data_retention_period", "retention_period", 50),
    ],
)
def test_file_settings_page_post_the_right_data_for_retention_period_and_link_text(
    client_request,
    service_one,
    fake_uuid,
    endpoint,
    file_setting,
    updated_value,
    test_template_email_files_data,
    test_data_for_a_template_email_file,
    mocker,
):
    service_one["permissions"] += ["send_files_via_ui"]
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                email_files=test_template_email_files_data,
            )
        },
    )
    mock_post = mocker.patch("app.template_email_file_client.post")
    update_data = test_data_for_a_template_email_file
    update_data[file_setting] = updated_value
    client_request.post(
        endpoint,
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        template_email_file_id=test_data_for_a_template_email_file["id"],
        _data=update_data,
        _expected_status=302,
    )
    expected_url = f"/service/{SERVICE_ONE_ID}/templates/{fake_uuid}/template_email_files/{update_data['id']}"
    args, kwargs = mock_post.call_args

    assert args[0] == expected_url
    assert kwargs["data"][file_setting] == update_data[file_setting]


def test_file_settings_page_post_the_right_data_for_email_validation(
    client_request,
    service_one,
    fake_uuid,
    test_template_email_files_data,
    test_data_for_a_template_email_file,
    mocker,
):
    service_one["permissions"] += ["send_files_via_ui"]
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                email_files=test_template_email_files_data,
            )
        },
    )
    mock_post = mocker.patch("app.template_email_file_client.post")
    update_data = test_data_for_a_template_email_file
    update_data["validate_users_email"] = True
    # add "enabled" key to update_data in order for the test to work with the OnOffSettingForm
    update_data["enabled"] = True
    client_request.post(
        "main.change_email_validation",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        template_email_file_id=update_data["id"],
        _data=update_data,
        _expected_status=302,
    )
    del update_data["enabled"]
    expected_url = f"/service/{SERVICE_ONE_ID}/templates/{fake_uuid}/template_email_files/{update_data['id']}"
    args, kwargs = mock_post.call_args
    assert args[0] == expected_url
    assert kwargs["data"]["validate_users_email"] is True


def test_change_retention_period_page(
    client_request,
    service_one,
    fake_uuid,
    test_template_email_files_data,
    mocker,
):
    service_one["permissions"] += ["send_files_via_ui"]
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                email_files=test_template_email_files_data,
            )
        },
    )
    page = client_request.get(
        "main.change_data_retention_period",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        template_email_file_id=test_template_email_files_data[0]["id"],
    )
    assert page.select_one("h1").string.strip() == "How long should the file be available for"
    assert page.select_one("label").string.strip() == "Number of weeks available to recipients"
    assert page.select_one("button[type=submit]").string.strip() == "Continue"


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
        "main.upload_template_email_files",
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
        "main.upload_template_email_files",
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
        "main.upload_template_email_files",
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
                "main.upload_template_email_files",
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
                "main.upload_template_email_files",
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
            "main.upload_template_email_files",
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


@pytest.mark.parametrize(
    "template_content",
    (
        "This is a file with a file placeholder ((tests/test_pdf_files/one_page_pdf.pdf))",
        "This is a file with a file placeholder ((tests/test_pdf_files/ONE-PAGE PDF.PDF))",
    ),
)
def test_upload_file_does_not_update_template_when_placeholder_already_exists(
    client_request,
    fake_uuid,
    service_one,
    mocker,
    template_content,
):
    service_one["permissions"] += ["send_files_via_ui"]
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                content=template_content,
            )
        },
    )
    mock_antivirus = mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    mock_s3 = mocker.patch("app.s3_client.s3_template_email_file_upload_client.utils_s3upload")
    mock_post = mocker.patch("app.template_email_file_client.post")
    mock_template_update = mocker.patch("app.service_api_client.update_service_template")
    with open("tests/test_pdf_files/one_page_pdf.pdf", "rb") as file:
        client_request.post(
            "main.upload_template_email_files",
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
            bucket_name="test-template-email-files",
            file_location=AnyStringMatching(rf"{SERVICE_ONE_ID}/{UUID4_REGEX_PATTERN}"),
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
                "validate_users_email": True,
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
            "main.upload_template_email_files",
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

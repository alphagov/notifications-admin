import base64
from functools import partial
from unittest.mock import Mock

import pytest
import werkzeug
from notifications_utils.template import LetterPreviewTemplate

from app import load_service_before_request
from app.models.branding import LetterBranding
from app.template_previews import (
    TemplatePreview,
    get_page_count_for_letter,
    sanitise_letter,
)
from tests.conftest import create_notification


@pytest.mark.parametrize(
    "partial_call, expected_page_argument",
    [
        (partial(TemplatePreview.from_utils_template), None),
        (partial(TemplatePreview.from_utils_template, page=99), 99),
    ],
)
def test_from_utils_template_calls_through(
    mocker,
    mock_get_service_letter_template,
    partial_call,
    expected_page_argument,
):
    mock_from_db = mocker.patch("app.template_previews.TemplatePreview.from_database_object")
    template = LetterPreviewTemplate(mock_get_service_letter_template(None, None)["data"])

    ret = partial_call(template, "foo")

    assert ret == mock_from_db.return_value
    mock_from_db.assert_called_once_with(template._template, "foo", template.values, page=expected_page_argument)


@pytest.mark.parametrize(
    "partial_call, expected_url",
    [
        (
            partial(TemplatePreview.from_database_object, filetype="bar"),
            "http://localhost:9999/preview.bar",
        ),
        (
            partial(TemplatePreview.from_database_object, filetype="baz"),
            "http://localhost:9999/preview.baz",
        ),
        (
            partial(TemplatePreview.from_database_object, filetype="bar", page=99),
            "http://localhost:9999/preview.bar?page=99",
        ),
    ],
)
@pytest.mark.parametrize(
    "letter_branding, expected_filename",
    [(LetterBranding({"filename": "hm-government"}), "hm-government"), (LetterBranding.from_id(None), None)],
)
def test_from_database_object_makes_request(
    mocker,
    client_request,
    partial_call,
    expected_url,
    letter_branding,
    expected_filename,
    mock_get_service_letter_template,
):
    # This test is calling `current_service` outside a Flask endpoint, so we need to make sure
    # `service` is in the `_request_ctx_stack` to avoid an error
    load_service_before_request()

    request_mock_returns = Mock(content="a", status_code="b", headers={"content-type": "image/png"})
    request_mock = mocker.patch("app.template_previews.requests.post", return_value=request_mock_returns)
    mocker.patch("app.template_previews.current_service", letter_branding=letter_branding)
    template = mock_get_service_letter_template("123", "456")["data"]

    response = partial_call(template=template)

    assert response[0] == "a"
    assert response[1] == "b"
    assert list(response[2]) == [("content-type", "image/png")]

    data = {
        "letter_contact_block": None,
        "template": template,
        "values": None,
        "filename": expected_filename,
    }
    headers = {"Authorization": "Token my-secret-key"}

    request_mock.assert_called_once_with(expected_url, json=data, headers=headers)


def test_from_notification_has_correct_args(mocker, client_request):
    # This test is calling `current_service` outside a Flask endpoint, so we need to make sure
    # `service` is in the `_request_ctx_stack` to avoid an error
    load_service_before_request()

    request_mock_returns = Mock(content="a", status_code="b", headers={"content-type": "image/png"})
    request_mock = mocker.patch("app.template_previews.requests.post", return_value=request_mock_returns)
    mocker.patch("app.template_previews.current_service", letter_branding=LetterBranding({"filename": "hm-government"}))

    notification = create_notification(
        service_id="abcd",
        template_type="letter",
        template_name="sample template",
        is_precompiled_letter=False,
    )
    response = TemplatePreview.from_notification(notification, "png")

    assert response[0] == "a"
    assert response[1] == "b"
    assert list(response[2]) == [("content-type", "image/png")]

    data = {
        "letter_contact_block": None,
        "template": notification["template"],
        "values": {"name": "Jo"},
        "filename": "hm-government",
    }
    headers = {"Authorization": "Token my-secret-key"}

    request_mock.assert_called_once_with("http://localhost:9999/preview.png", json=data, headers=headers)


def test_from_notification_rejects_precompiled_templates(mocker):
    notification = create_notification(
        service_id="abcd",
        template_type="letter",
        template_name="sample template",
        is_precompiled_letter=True,
    )

    with pytest.raises(werkzeug.exceptions.BadRequest):
        TemplatePreview.from_notification(notification, "png")


@pytest.mark.parametrize(
    "page_number, expected_url",
    [
        ("1", "http://localhost:9999/precompiled-preview.png?hide_notify=true"),
        ("2", "http://localhost:9999/precompiled-preview.png"),
    ],
)
def test_from_valid_pdf_file_makes_request(mocker, client_request, page_number, expected_url):
    mocker.patch("app.template_previews.extract_page_from_pdf", return_value=b"pdf page")
    request_mock = mocker.patch(
        "app.template_previews.requests.post",
        return_value=Mock(content="a", status_code="b", headers={"content-type": "image/png"}),
    )

    response = TemplatePreview.from_valid_pdf_file(b"pdf file", page_number)

    assert response == ("a", "b", {"content-type": "image/png"}.items())
    request_mock.assert_called_once_with(
        expected_url,
        data=base64.b64encode(b"pdf page").decode("utf-8"),
        headers={"Authorization": "Token my-secret-key"},
    )


def test_from_invalid_pdf_file_makes_request(mocker, client_request):
    mocker.patch("app.template_previews.extract_page_from_pdf", return_value=b"pdf page")
    request_mock = mocker.patch(
        "app.template_previews.requests.post",
        return_value=Mock(content="a", status_code="b", headers={"content-type": "image/png"}),
    )

    response = TemplatePreview.from_invalid_pdf_file(b"pdf file", "1")

    assert response == ("a", "b", {"content-type": "image/png"}.items())
    request_mock.assert_called_once_with(
        "http://localhost:9999/precompiled/overlay.png?page_number=1",
        data=b"pdf page",
        headers={"Authorization": "Token my-secret-key"},
    )


@pytest.mark.parametrize("template_type", ["email", "sms"])
def test_page_count_returns_none_for_non_letter_templates(template_type):
    assert get_page_count_for_letter({"template_type": template_type}) is None


@pytest.mark.parametrize(
    "partial_call, expected_template_preview_args",
    [
        (partial(get_page_count_for_letter), ({"template_type": "letter"}, "json", None)),
        (
            partial(get_page_count_for_letter, values={"foo": "bar"}),
            ({"template_type": "letter"}, "json", {"foo": "bar"}),
        ),
    ],
)
def test_page_count_unpacks_from_json_response(
    mocker,
    partial_call,
    expected_template_preview_args,
):
    mock_template_preview = mocker.patch("app.template_previews.TemplatePreview.from_database_object")
    mock_template_preview.return_value = (b'{"count": 99}', 200, {})

    assert partial_call({"template_type": "letter"}) == 99
    mock_template_preview.assert_called_once_with(*expected_template_preview_args)


def test_from_example_template_makes_request(mocker, client_request):
    request_mock = mocker.patch("app.template_previews.requests.post")
    template = {}
    filename = "geo"

    TemplatePreview.from_example_template(template, filename)

    request_mock.assert_called_once_with(
        "http://localhost:9999/preview.png",
        headers={"Authorization": "Token my-secret-key"},
        json={"values": None, "template": template, "filename": filename, "letter_contact_block": None},
    )


@pytest.mark.parametrize("allow_international_letters, query_param_value", [[False, "false"], [True, "true"]])
def test_sanitise_letter_calls_template_preview_sanitise_endpoint_with_file(
    mocker,
    client_request,
    allow_international_letters,
    query_param_value,
    fake_uuid,
):
    request_mock = mocker.patch("app.template_previews.requests.post")

    sanitise_letter("pdf_data", upload_id=fake_uuid, allow_international_letters=allow_international_letters)

    expected_url = (
        f"http://localhost:9999/precompiled/sanitise"
        f"?allow_international_letters={query_param_value}"
        f"&upload_id={fake_uuid}"
    )

    request_mock.assert_called_once_with(
        expected_url, headers={"Authorization": "Token my-secret-key"}, data="pdf_data"
    )


def test_sanitise_letter_calls_template_preview_sanitise_endpoint_with_file_for_an_attachment(
    mocker,
    client_request,
    fake_uuid,
):
    request_mock = mocker.patch("app.template_previews.requests.post")

    sanitise_letter("pdf_data", upload_id=fake_uuid, allow_international_letters=False, is_an_attachment=True)

    expected_url = (
        f"http://localhost:9999/precompiled/sanitise"
        f"?allow_international_letters=false"
        f"&upload_id={fake_uuid}"
        f"&is_an_attachment=true"
    )

    request_mock.assert_called_once_with(
        expected_url, headers={"Authorization": "Token my-secret-key"}, data="pdf_data"
    )

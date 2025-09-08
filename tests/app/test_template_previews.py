import base64
from unittest.mock import Mock

import pytest
from werkzeug.exceptions import BadRequest, NotFound

from app import load_service_before_request, template_preview_client
from app.models.branding import LetterBranding
from app.models.service import Service
from tests.conftest import create_notification


@pytest.mark.parametrize(
    "extra_kwargs, expected_url",
    [
        (
            {"filetype": "bar"},
            "http://localhost:9999/preview.bar",
        ),
        (
            {"filetype": "baz"},
            "http://localhost:9999/preview.baz",
        ),
        (
            {"filetype": "bar", "page": 99},
            "http://localhost:9999/preview.bar?page=99",
        ),
    ],
)
@pytest.mark.parametrize(
    "letter_branding, expected_filename",
    [(LetterBranding({"filename": "hm-government"}), "hm-government"), (LetterBranding.from_id(None), None)],
)
def test_get_preview_for_templated_letter_makes_request(
    client_request,
    mocker,
    service_one,
    extra_kwargs,
    expected_url,
    letter_branding,
    expected_filename,
    mock_get_service_letter_template,
    mock_onwards_request_headers,
):
    request_mock_returns = Mock(content="a", status_code="b", headers={"content-type": "image/png"})
    request_mock = mocker.patch("app.template_preview_client.requests_session.post", return_value=request_mock_returns)
    service = mocker.Mock(spec=Service, letter_branding=letter_branding)
    template = mock_get_service_letter_template("123", "456")["data"]

    response = template_preview_client.get_preview_for_templated_letter(
        db_template=template,
        service=service,
        **extra_kwargs,
    )

    assert response[0] == "a"
    assert response[1] == "b"
    assert list(response[2]) == [("content-type", "image/png")]

    data = {
        "letter_contact_block": None,
        "template": template,
        "values": None,
        "filename": expected_filename,
    }
    headers = {
        "Authorization": "Token my-secret-key",
        "some-onwards": "request-headers",
    }

    request_mock.assert_called_once_with(expected_url, json=data, headers=headers)


@pytest.mark.parametrize(
    "extra_args, expected_filename",
    (
        ({}, "hm-government"),
        ({"branding_filename": "custom"}, "custom"),
    ),
)
def test_get_preview_for_templated_letter_allows_service_branding_to_be_overridden(
    client_request,
    mocker,
    extra_args,
    expected_filename,
    mock_get_service_letter_template,
):
    load_service_before_request()

    request_mock = mocker.patch("app.template_preview_client.requests_session.post")
    service = mocker.Mock(spec=Service, letter_branding=LetterBranding({"filename": "hm-government"}))

    template_preview_client.get_preview_for_templated_letter(
        db_template=create_notification(template_type="letter")["template"],
        filetype="png",
        service=service,
        **extra_args,
    )

    assert request_mock.call_args[1]["json"]["filename"] == expected_filename


def test_get_preview_for_templated_letter_from_notification_has_correct_args(
    client_request,
    mocker,
    mock_onwards_request_headers,
):
    request_mock_returns = Mock(content="a", status_code="b", headers={"content-type": "image/png"})
    request_mock = mocker.patch("app.template_preview_client.requests_session.post", return_value=request_mock_returns)
    service = mocker.Mock(spec=Service, letter_branding=LetterBranding({"filename": "hm-government"}))

    notification = create_notification(
        service_id="abcd",
        template_type="letter",
        template_name="sample template",
        is_precompiled_letter=False,
    )
    response = template_preview_client.get_preview_for_templated_letter(
        notification["template"],
        "png",
        notification["personalisation"],
        service=service,
    )

    assert response[0] == "a"
    assert response[1] == "b"
    assert list(response[2]) == [("content-type", "image/png")]

    data = {
        "letter_contact_block": None,
        "template": notification["template"],
        "values": {"name": "Jo"},
        "filename": "hm-government",
    }
    headers = {
        "Authorization": "Token my-secret-key",
        "some-onwards": "request-headers",
    }

    request_mock.assert_called_once_with("http://localhost:9999/preview.png", json=data, headers=headers)


def test_get_preview_for_templated_letter_from_notification_rejects_precompiled_templates(notify_admin, mocker):
    notification = create_notification(
        service_id="abcd",
        template_type="letter",
        template_name="sample template",
        is_precompiled_letter=True,
    )

    with pytest.raises(ValueError):
        template_preview_client.get_preview_for_templated_letter(
            notification["template"], "png", notification["personalisation"]
        )


@pytest.mark.parametrize("template_type", ("email", "sms"))
@pytest.mark.parametrize("file_type", ("pdf", "png"))
def test_get_preview_for_templated_letter_from_notification_404s_non_letter_templates(
    notify_admin,
    mocker,
    template_type,
    file_type,
):
    notification = create_notification(
        service_id="abcd",
        template_type=template_type,
        template_name="sample template",
    )

    with pytest.raises(NotFound):
        template_preview_client.get_preview_for_templated_letter(
            notification["template"], file_type, notification["personalisation"]
        )


def test_get_preview_for_templated_letter_from_notification_400s_for_page_of_pdf(notify_admin, mocker):
    notification = create_notification(
        service_id="abcd",
        template_type="letter",
        template_name="sample template",
    )

    with pytest.raises(BadRequest):
        template_preview_client.get_preview_for_templated_letter(
            notification["template"],
            "pdf",
            page=1,
        )


@pytest.mark.parametrize(
    "page_number, expected_url",
    [
        ("1", "http://localhost:9999/precompiled-preview.png?hide_notify=true"),
        ("2", "http://localhost:9999/precompiled-preview.png"),
    ],
)
def test_get_png_for_valid_pdf_page_makes_request(
    client_request,
    mocker,
    mock_onwards_request_headers,
    page_number,
    expected_url,
):
    mocker.patch("app.template_previews.extract_page_from_pdf", return_value=b"pdf page")
    request_mock = mocker.patch(
        "app.template_preview_client.requests_session.post",
        return_value=Mock(content="a", status_code="b", headers={"content-type": "image/png"}),
    )

    response = template_preview_client.get_png_for_valid_pdf_page(b"pdf file", page_number)

    assert response == ("a", "b", {"content-type": "image/png"}.items())
    request_mock.assert_called_once_with(
        expected_url,
        data=base64.b64encode(b"pdf page").decode("utf-8"),
        headers={
            "Authorization": "Token my-secret-key",
            "some-onwards": "request-headers",
        },
    )


def test_get_png_for_invalid_pdf_page_makes_request(
    client_request,
    mocker,
    mock_onwards_request_headers,
):
    mocker.patch("app.template_previews.extract_page_from_pdf", return_value=b"pdf page")
    request_mock = mocker.patch(
        "app.template_preview_client.requests_session.post",
        return_value=Mock(content="a", status_code="b", headers={"content-type": "image/png"}),
    )

    response = template_preview_client.get_png_for_invalid_pdf_page(b"pdf file", "1")

    assert response == ("a", "b", {"content-type": "image/png"}.items())
    request_mock.assert_called_once_with(
        "http://localhost:9999/precompiled/overlay.png?page_number=1&is_an_attachment=False",
        data=b"pdf page",
        headers={
            "Authorization": "Token my-secret-key",
            "some-onwards": "request-headers",
        },
    )


@pytest.mark.parametrize("template_type", ["email", "sms"])
def test_page_count_returns_none_for_non_letter_templates(notify_admin, template_type, mocker):
    assert (
        template_preview_client.get_page_counts_for_letter(
            {"template_type": template_type},
            service=mocker.Mock(),
        )
        is None
    )


@pytest.mark.parametrize(
    "values, expected_template_preview_args",
    [
        (None, ({"template_type": "letter"}, "json", None)),
        (
            {"foo": "bar"},
            ({"template_type": "letter"}, "json", {"foo": "bar"}),
        ),
    ],
)
def test_page_count_makes_a_call_to_template_preview_and_gets_page_count(
    client_request,
    mocker,
    mock_get_service_letter_template,
    mock_onwards_request_headers,
    values,
    expected_template_preview_args,
):
    request_mock_returns = Mock(
        content=b'{"count": 9, "welsh_page_count": 4, "attachment_page_count": 1}', status_code=200
    )
    request_mock = mocker.patch("app.template_preview_client.requests_session.post", return_value=request_mock_returns)
    service = mocker.Mock(spec=Service, letter_branding=LetterBranding({"filename": "hm-government"}))
    template = mock_get_service_letter_template("123", "456")["data"]

    assert template_preview_client.get_page_counts_for_letter(
        template,
        values=values,
        service=service,
    ) == {
        "count": 9,
        "welsh_page_count": 4,
        "attachment_page_count": 1,
    }

    data = {
        "letter_contact_block": None,
        "template": template,
        "values": values,
        "filename": "hm-government",
    }
    headers = {
        "Authorization": "Token my-secret-key",
        "some-onwards": "request-headers",
    }

    request_mock.assert_called_once_with("http://localhost:9999/get-page-count", json=data, headers=headers)


@pytest.mark.parametrize("allow_international_letters, query_param_value", [[False, "false"], [True, "true"]])
def test_sanitise_letter_calls_template_preview_sanitise_endpoint_with_file(
    client_request,
    mocker,
    mock_onwards_request_headers,
    allow_international_letters,
    query_param_value,
    fake_uuid,
):
    request_mock = mocker.patch("app.template_preview_client.requests_session.post")

    template_preview_client.sanitise_letter(
        "pdf_data", upload_id=fake_uuid, allow_international_letters=allow_international_letters
    )

    expected_url = (
        f"http://localhost:9999/precompiled/sanitise"
        f"?allow_international_letters={query_param_value}"
        f"&upload_id={fake_uuid}"
    )

    request_mock.assert_called_once_with(
        expected_url,
        headers={
            "Authorization": "Token my-secret-key",
            "some-onwards": "request-headers",
        },
        data="pdf_data",
    )


def test_sanitise_letter_calls_template_preview_sanitise_endpoint_with_file_for_an_attachment(
    client_request,
    mocker,
    mock_onwards_request_headers,
    fake_uuid,
):
    request_mock = mocker.patch("app.template_preview_client.requests_session.post")

    template_preview_client.sanitise_letter(
        "pdf_data", upload_id=fake_uuid, allow_international_letters=False, is_an_attachment=True
    )

    expected_url = (
        f"http://localhost:9999/precompiled/sanitise"
        f"?allow_international_letters=false"
        f"&upload_id={fake_uuid}"
        f"&is_an_attachment=true"
    )

    request_mock.assert_called_once_with(
        expected_url,
        headers={
            "Authorization": "Token my-secret-key",
            "some-onwards": "request-headers",
        },
        data="pdf_data",
    )

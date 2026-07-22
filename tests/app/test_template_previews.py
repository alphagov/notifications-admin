import base64
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from notifications_utils.testing.comparisons import AnySupersetOf
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
@pytest.mark.parametrize(
    "date_kwargs, expected_date_string_in_json",
    (
        ({}, None),
        ({"date": None}, None),
        ({"date": datetime(2021, 2, 3, 4, 5, 6, tzinfo=UTC)}, "2021-02-03T04:05:06+00:00"),
    ),
)
def test_get_preview_for_templated_letter_makes_request(
    client_request,
    service_one,
    extra_kwargs,
    expected_url,
    letter_branding,
    expected_filename,
    date_kwargs,
    expected_date_string_in_json,
    mock_get_service_letter_template,
    mock_onwards_request_headers,
    requests_mock,
):
    requests_mock.post(
        expected_url,
        request_headers={
            "Authorization": "Token my-secret-key",
            "some-onwards": "request-headers",
        },
        content=b"a",
        status_code=200,
        headers={"content-type": "image/png"},
    )
    service = Mock(spec=Service, letter_branding=letter_branding)
    template = mock_get_service_letter_template("123", "456")["data"]

    response = template_preview_client.get_preview_for_templated_letter(
        db_template=template,
        service=service,
        **(extra_kwargs | date_kwargs),
    )

    assert response == (b"a", 200, [("content-type", "image/png")])

    data = {
        "letter_contact_block": None,
        "template": template,
        "values": None,
        "filename": expected_filename,
        "date": expected_date_string_in_json,
    }

    assert len(requests_mock.request_history) == 1
    assert requests_mock.request_history[0].json() == data


@pytest.mark.parametrize(
    "extra_args, expected_filename",
    (
        ({}, "hm-government"),
        ({"branding_filename": "custom"}, "custom"),
    ),
)
def test_get_preview_for_templated_letter_allows_service_branding_to_be_overridden(
    client_request,
    extra_args,
    expected_filename,
    mock_onwards_request_headers,
    mock_get_service_letter_template,
    requests_mock,
):
    load_service_before_request()

    requests_mock.post(
        "http://localhost:9999/preview.png",
        request_headers={
            "Authorization": "Token my-secret-key",
            "some-onwards": "request-headers",
        },
        content=b"a",
        status_code=200,
        headers={"content-type": "image/png"},
    )
    service = Mock(spec=Service, letter_branding=LetterBranding({"filename": "hm-government"}))

    template_preview_client.get_preview_for_templated_letter(
        db_template=create_notification(template_type="letter")["template"],
        filetype="png",
        service=service,
        **extra_args,
    )

    assert len(requests_mock.request_history) == 1
    assert requests_mock.request_history[0].json() == AnySupersetOf(
        {
            "filename": expected_filename,
        }
    )


def test_get_preview_for_templated_letter_from_notification_has_correct_args(
    client_request,
    mock_onwards_request_headers,
    requests_mock,
):
    requests_mock.post(
        "http://localhost:9999/preview.png",
        request_headers={
            "Authorization": "Token my-secret-key",
            "some-onwards": "request-headers",
        },
        content=b"a",
        status_code=200,
        headers={"content-type": "image/png"},
    )
    service = Mock(spec=Service, letter_branding=LetterBranding({"filename": "hm-government"}))

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

    assert response == (b"a", 200, [("content-type", "image/png")])

    assert len(requests_mock.request_history) == 1
    assert requests_mock.request_history[0].json() == {
        "letter_contact_block": None,
        "template": notification["template"],
        "values": {"name": "Jo"},
        "filename": "hm-government",
        "date": None,
    }


def test_get_preview_for_templated_letter_from_notification_rejects_precompiled_templates(notify_admin, requests_mock):
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

    assert not requests_mock.request_history


@pytest.mark.parametrize("template_type", ("email", "sms"))
@pytest.mark.parametrize("file_type", ("pdf", "png"))
def test_get_preview_for_templated_letter_from_notification_404s_non_letter_templates(
    notify_admin,
    template_type,
    file_type,
    requests_mock,
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

    assert not requests_mock.request_history


def test_get_preview_for_templated_letter_from_notification_400s_for_page_of_pdf(notify_admin, requests_mock):
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

    assert not requests_mock.request_history


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
    requests_mock,
):
    mocker.patch("app.template_previews.extract_page_from_pdf", return_value=b"pdf page")
    requests_mock.post(
        expected_url,
        request_headers={
            "Authorization": "Token my-secret-key",
            "some-onwards": "request-headers",
        },
        content=b"a",
        status_code=200,
        headers={"content-type": "image/png"},
    )

    response = template_preview_client.get_png_for_valid_pdf_page(b"pdf file", page_number)

    assert response == (b"a", 200, {"content-type": "image/png"}.items())

    assert len(requests_mock.request_history) == 1
    assert requests_mock.request_history[0].body == base64.b64encode(b"pdf page").decode("utf-8")


def test_get_png_for_invalid_pdf_page_makes_request(
    client_request,
    mocker,
    mock_onwards_request_headers,
    requests_mock,
):
    mocker.patch("app.template_previews.extract_page_from_pdf", return_value=b"pdf page")
    requests_mock.post(
        "http://localhost:9999/precompiled/overlay.png?page_number=1&is_an_attachment=False",
        request_headers={
            "Authorization": "Token my-secret-key",
            "some-onwards": "request-headers",
        },
        content=b"a",
        status_code=200,
        headers={"content-type": "image/png"},
    )

    response = template_preview_client.get_png_for_invalid_pdf_page(b"pdf file", "1")

    assert response == (b"a", 200, {"content-type": "image/png"}.items())

    assert len(requests_mock.request_history) == 1
    assert requests_mock.request_history[0].body == b"pdf page"


@pytest.mark.parametrize("template_type", ["email", "sms"])
def test_page_count_returns_none_for_non_letter_templates(notify_admin, template_type):
    assert (
        template_preview_client.get_page_counts_for_letter(
            {"template_type": template_type},
            service=Mock(),
        )
        is None
    )


@pytest.mark.parametrize(
    "values",
    (
        None,
        {"foo": "bar"},
    ),
)
def test_page_count_makes_a_call_to_template_preview_and_gets_page_count(
    client_request,
    mock_get_service_letter_template,
    mock_onwards_request_headers,
    values,
    requests_mock,
):
    requests_mock.post(
        "http://localhost:9999/get-page-count",
        request_headers={
            "Authorization": "Token my-secret-key",
            "some-onwards": "request-headers",
        },
        content=b'{"count": 9, "welsh_page_count": 4, "attachment_page_count": 1}',
        status_code=200,
        headers={"content-type": "application/json"},
    )

    service = Mock(spec=Service, letter_branding=LetterBranding({"filename": "hm-government"}))
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

    assert len(requests_mock.request_history) == 1
    assert requests_mock.request_history[0].json() == {
        "letter_contact_block": None,
        "template": template,
        "values": values,
        "filename": "hm-government",
    }


@pytest.mark.parametrize("allow_international_letters, query_param_value", [[False, "false"], [True, "true"]])
def test_sanitise_letter_calls_template_preview_sanitise_endpoint_with_file(
    client_request,
    mock_onwards_request_headers,
    allow_international_letters,
    query_param_value,
    fake_uuid,
    requests_mock,
):
    expected_url = (
        f"http://localhost:9999/precompiled/sanitise"
        f"?allow_international_letters={query_param_value}"
        f"&upload_id={fake_uuid}"
    )
    requests_mock.post(
        expected_url,
        request_headers={
            "Authorization": "Token my-secret-key",
            "some-onwards": "request-headers",
        },
    )

    template_preview_client.sanitise_letter(
        b"pdf_data", upload_id=fake_uuid, allow_international_letters=allow_international_letters
    )

    assert len(requests_mock.request_history) == 1
    assert requests_mock.request_history[0].body == b"pdf_data"


def test_sanitise_letter_calls_template_preview_sanitise_endpoint_with_file_for_an_attachment(
    client_request,
    mock_onwards_request_headers,
    fake_uuid,
    requests_mock,
):
    expected_url = (
        f"http://localhost:9999/precompiled/sanitise"
        f"?allow_international_letters=false"
        f"&upload_id={fake_uuid}"
        f"&is_an_attachment=true"
    )
    requests_mock.post(
        expected_url,
        request_headers={
            "Authorization": "Token my-secret-key",
            "some-onwards": "request-headers",
        },
    )

    template_preview_client.sanitise_letter(
        b"pdf_data", upload_id=fake_uuid, allow_international_letters=False, is_an_attachment=True
    )

    assert len(requests_mock.request_history) == 1
    assert requests_mock.request_history[0].body == b"pdf_data"

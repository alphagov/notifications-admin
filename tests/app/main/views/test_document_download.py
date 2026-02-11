from unittest.mock import call
from uuid import UUID, uuid4

import pytest
from flask import abort, url_for
from notifications_utils.base64_uuid import uuid_to_base64
from notifications_utils.testing.comparisons import RestrictedAny

from app.models.user import User
from tests import service_json
from tests.conftest import (
    SERVICE_ONE_ID,
    create_template,
    normalize_spaces,
)


@pytest.mark.parametrize(
    "endpoint",
    (
        ".document_download_index",
        ".document_download_confirm_email_address",
    ),
)
def test_redirect_if_user_not_signed_in(client_request, fake_uuid, endpoint):
    client_request.logout()
    client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=fake_uuid,
        _expected_redirect=url_for(
            "main.sign_in",
            next=url_for(endpoint, service_id=SERVICE_ONE_ID, document_id=fake_uuid, key=fake_uuid),
        ),
    )


@pytest.mark.parametrize(
    "endpoint",
    (
        ".document_download_index",
        ".document_download_confirm_email_address",
    ),
)
def test_403_if_user_does_not_have_permission_to_see_template(client_request, fake_uuid, mocker, endpoint):
    mock_get_template = mocker.patch(
        "app.models.service.Service.get_template_with_user_permission_or_403",
        side_effect=lambda *args, **kwargs: abort(403),
    )
    client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        document_id=uuid4(),
        key=uuid_to_base64(fake_uuid),
        _expected_status=403,
    )
    assert mock_get_template.call_args_list == [
        call(UUID(fake_uuid), RestrictedAny(lambda u: isinstance(u, User)), must_be_of_type="email"),
    ]


@pytest.mark.parametrize(
    "query_string",
    (
        "",
        "?key=",
        "?key=not-valid-base64-uuid",
    ),
)
@pytest.mark.parametrize(
    "endpoint",
    (
        ".document_download_index",
        ".document_download_confirm_email_address",
    ),
)
def test_404_if_bad_template_id(
    client_request,
    fake_uuid,
    query_string,
    endpoint,
):
    client_request.get_url(
        url_for(
            endpoint,
            service_id=SERVICE_ONE_ID,
            document_id=fake_uuid,
        )
        + query_string,
        _expected_status=404,
    )


@pytest.mark.parametrize(
    "endpoint",
    (
        ".document_download_index",
        ".document_download_confirm_email_address",
    ),
)
def test_404_if_not_email_template(
    client_request,
    fake_uuid,
    mock_get_service_template,
    endpoint,
):
    client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
        _expected_status=404,
    )


@pytest.mark.parametrize(
    "email_files",
    (
        [],
        [
            {
                "id": UUID(int=1, version=4),
                "filename": "invite.pdf",
                "link_text": None,
                "retention_period": 90,
                "validate_users_email": False,
            },
        ],
    ),
)
@pytest.mark.parametrize(
    "endpoint",
    (
        ".document_download_index",
        ".document_download_confirm_email_address",
    ),
)
def test_404_if_document_not_found(
    client_request,
    fake_uuid,
    mocker,
    email_files,
    endpoint,
):
    email_template = create_template(
        template_id=fake_uuid,
        template_type="email",
        email_files=email_files,
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})
    client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        document_id=UUID(int=2, version=4),
        key=uuid_to_base64(fake_uuid),
        _expected_status=404,
    )


@pytest.mark.parametrize(
    "contact_link_value, expected_paragraphs, expected_link_text, expected_url",
    (
        (
            None,
            [
                "Test Service sent you a file to download.",
                "Continue",
            ],
            None,
            None,
        ),
        (
            "http://example.com/",
            [
                "Test Service sent you a file to download.",
                "Continue",
                "If you have any questions, contact Test Service.",
            ],
            "contact Test Service",
            "http://example.com/",
        ),
        (
            "me@example.com",
            [
                "Test Service sent you a file to download.",
                "Continue",
                "If you have any questions, email me@example.com.",
            ],
            "me@example.com",
            "mailto:me@example.com",
        ),
        (
            "0207 123 4567",
            [
                "Test Service sent you a file to download.",
                "Continue",
                "If you have any questions, call 0207 123 4567.",
            ],
            None,
            None,
        ),
    ),
)
def test_landing_page(
    client_request,
    fake_uuid,
    contact_link_value,
    expected_paragraphs,
    expected_link_text,
    expected_url,
    mocker,
):
    email_template = create_template(
        template_id=fake_uuid,
        template_type="email",
        email_files=[
            {
                "id": fake_uuid,
                "filename": "invite.pdf",
                "link_text": None,
                "retention_period": 90,
                "validate_users_email": False,
            },
        ],
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})
    mocker.patch(
        "app.service_api_client.get_service",
        return_value={"data": service_json(SERVICE_ONE_ID, contact_link=contact_link_value)},
    )
    page = client_request.get(
        ".document_download_index",
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
    )
    assert normalize_spaces(page.select_one("main h1")) == "You have a file to download"
    assert [
        normalize_spaces(p.text) for p in page.select(".govuk-grid-column-two-thirds > p.govuk-body")
    ] == expected_paragraphs

    button = page.select_one("a.govuk-button")
    assert button["href"] == url_for(
        "main.document_download_confirm_email_address",
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
    )
    assert normalize_spaces(button.text) == "Continue"

    link = page.select_one(".govuk-grid-column-two-thirds > p.govuk-body a.govuk-link")
    assert not expected_url or link["href"] == expected_url
    assert normalize_spaces(link) == expected_link_text


def test_confirm_email_page_redirects_if_confirmation_not_required(
    client_request,
    fake_uuid,
    mocker,
):
    email_template = create_template(
        template_id=fake_uuid,
        template_type="email",
        email_files=[
            {
                "id": fake_uuid,
                "filename": "invite.pdf",
                "link_text": None,
                "retention_period": 90,
                "validate_users_email": False,
            },
        ],
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})
    client_request.get(
        ".document_download_confirm_email_address",
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
        _expected_redirect="https://www.example.com",
    )


@pytest.mark.parametrize(
    "contact_link_value, expected_paragraphs, expected_link_text, expected_url",
    (
        (
            None,
            [
                "For security, we need to confirm the email address the file was sent to before you can download it.",
            ],
            None,
            None,
        ),
        (
            "http://example.com/",
            [
                "For security, we need to confirm the email address the file was sent to before you can download it.",
                "If you have any questions, contact Test Service.",
            ],
            "contact Test Service",
            "http://example.com/",
        ),
        (
            "me@example.com",
            [
                "For security, we need to confirm the email address the file was sent to before you can download it.",
                "If you have any questions, email me@example.com.",
            ],
            "me@example.com",
            "mailto:me@example.com",
        ),
        (
            "0207 123 4567",
            [
                "For security, we need to confirm the email address the file was sent to before you can download it.",
                "If you have any questions, call 0207 123 4567.",
            ],
            None,
            None,
        ),
    ),
)
def test_confirm_email_page_shows_form_if_confirmation_required(
    client_request,
    fake_uuid,
    mocker,
    contact_link_value,
    expected_paragraphs,
    expected_link_text,
    expected_url,
):
    mocker.patch(
        "app.service_api_client.get_service",
        return_value={"data": service_json(SERVICE_ONE_ID, contact_link=contact_link_value)},
    )
    email_template = create_template(
        template_id=fake_uuid,
        template_type="email",
        email_files=[
            {
                "id": fake_uuid,
                "filename": "invite.pdf",
                "link_text": None,
                "retention_period": 90,
                "validate_users_email": True,
            },
        ],
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})
    page = client_request.get(
        ".document_download_confirm_email_address",
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
    )

    assert normalize_spaces(page.select_one("h1").text) == "Confirm your email address"

    form = page.select_one("form")
    assert form["action"] == url_for(
        ".document_download_confirm_email_address",
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
    )
    assert form["autocomplete"] == "off"
    assert form["novalidate"] == ""
    assert form["method"] == "post"
    assert normalize_spaces(form.select_one("label[for=email_address]").text) == "Email address"
    assert "value" not in form.select_one("input[type=email][name=email_address]")
    assert normalize_spaces(form.select_one("button.govuk-button").text) == "Continue"

    assert [
        normalize_spaces(p.text) for p in page.select(".govuk-grid-column-two-thirds > p.govuk-body")
    ] == expected_paragraphs

    link = page.select_one(".govuk-grid-column-two-thirds > p.govuk-body a.govuk-link")
    assert not expected_url or link["href"] == expected_url
    assert normalize_spaces(link) == expected_link_text


@pytest.mark.parametrize(
    "email_address, expected_error",
    (
        ("", "Enter email address"),
        ("testing", "Not a valid email address"),
        (
            "not-current-user@example.gov.uk",
            (
                "This is not the email address the file was sent to."
                "To confirm the file was meant for you, enter the email address Test Service sent the file to."
            ),
        ),
    ),
)
def test_confirm_email_page_shows_errors(
    client_request,
    fake_uuid,
    mocker,
    email_address,
    expected_error,
):
    email_template = create_template(
        template_id=fake_uuid,
        template_type="email",
        email_files=[
            {
                "id": fake_uuid,
                "filename": "invite.pdf",
                "link_text": None,
                "retention_period": 90,
                "validate_users_email": True,
            },
        ],
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})
    page = client_request.post(
        ".document_download_confirm_email_address",
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
        _data={
            "email_address": email_address,
        },
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one(".govuk-error-summary").text) == f"There is a problem {expected_error}"
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == f"Error: {expected_error}"


@pytest.mark.parametrize(
    "email_address",
    (
        "test@user.gov.uk",
        "TEST@USER.GOV.UK",
        "  test@user.gov.uk  ",
    ),
)
def test_confirm_email_page_redirects_for_correct_email(
    client_request,
    fake_uuid,
    mocker,
    email_address,
):
    email_template = create_template(
        template_id=fake_uuid,
        template_type="email",
        email_files=[
            {
                "id": fake_uuid,
                "filename": "invite.pdf",
                "link_text": None,
                "retention_period": 90,
                "validate_users_email": True,
            },
        ],
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})
    client_request.post(
        ".document_download_confirm_email_address",
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
        _data={
            "email_address": email_address,
        },
        _expected_redirect="https://www.example.com",
    )


@pytest.mark.parametrize(
    "endpoint, expected_banner_text",
    (
        (
            ".document_download_index",
            (
                "Preview "
                "This is a preview of the page your recipients will see "
                "To change or remove the file, edit the email template."
            ),
        ),
        (
            ".document_download_confirm_email_address",
            (
                "Preview "
                "This is a preview of the page your recipients will see "
                "To change or remove the file, edit the email template. "
                "To continue, enter the email address you use to sign in to Notify."
            ),
        ),
        # TODO: Add test case for the download endpoint once built
    ),
)
def test_banner_on_all_pages(
    client_request,
    fake_uuid,
    mocker,
    endpoint,
    expected_banner_text,
):
    email_template = create_template(
        template_id=fake_uuid,
        template_type="email",
        email_files=[
            {
                "id": fake_uuid,
                "filename": "invite.pdf",
                "link_text": None,
                "retention_period": 90,
                "validate_users_email": True,
            },
        ],
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})
    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
    )
    banner = page.select_one(".govuk-notification-banner")
    assert normalize_spaces(banner.text) == expected_banner_text
    assert banner.select_one("a")["href"] == url_for(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

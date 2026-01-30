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


def test_redirect_if_user_not_signed_in(
    client_request,
    fake_uuid,
):
    client_request.logout()
    client_request.get(
        ".document_download_index",
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=fake_uuid,
        _expected_redirect=url_for(
            "main.sign_in",
            next=url_for(".document_download_index", service_id=SERVICE_ONE_ID, document_id=fake_uuid, key=fake_uuid),
        ),
    )


def test_403_if_user_does_not_have_permission_to_see_template(
    client_request,
    fake_uuid,
    mocker,
):
    mock_get_template = mocker.patch(
        "app.models.service.Service.get_template_with_user_permission_or_403",
        side_effect=lambda *args, **kwargs: abort(403),
    )
    client_request.get(
        ".document_download_index",
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
def test_404_if_bad_template_id(
    client_request,
    fake_uuid,
    query_string,
):
    client_request.get_url(
        url_for(
            ".document_download_index",
            service_id=SERVICE_ONE_ID,
            document_id=fake_uuid,
        )
        + query_string,
        _expected_status=404,
    )


def test_404_if_not_email_template(
    client_request,
    fake_uuid,
    mock_get_service_template,
):
    client_request.get(
        ".document_download_index",
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
def test_404_if_document_not_found(
    client_request,
    fake_uuid,
    mocker,
    email_files,
):
    email_template = create_template(
        template_id=fake_uuid,
        template_type="email",
        email_files=email_files,
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})
    client_request.get(
        ".document_download_index",
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
        return_value={"data": service_json(contact_link=contact_link_value)},
    )
    page = client_request.get(
        ".document_download_index",
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
    )
    assert normalize_spaces(page.select_one("main h1")) == "You have a file to download"
    assert [normalize_spaces(p.text) for p in page.select("main p.govuk-body")] == expected_paragraphs

    button = page.select_one("a.govuk-button")
    assert button["href"] == "https://www.example.com"
    assert normalize_spaces(button.text) == "Continue"

    link = page.select_one("main p.govuk-body a.govuk-link")
    assert not expected_url or link["href"] == expected_url
    assert normalize_spaces(link) == expected_link_text

from uuid import UUID

import pytest
from flask import url_for

from app import Organisation
from tests import organisation_json
from tests.conftest import ORGANISATION_ID, SERVICE_ONE_ID, normalize_spaces


def test_organisation_email_branding_page_is_not_accessible_by_non_platform_admin(
    client_request,
    organisation_one,
    mock_get_organisation,
):
    page = client_request.get("main.organisation_email_branding", org_id=organisation_one["id"], _expected_status=403)
    assert page


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "default_email_branding, expected_branding_options",
    (
        [None, {"GOV.UK (default)", "Email branding name 1", "Email branding name 2"}],
        ["email-branding-2-id", {"Email branding name 2 (default)", "Email branding name 1"}],
    ),
)
def test_organisation_email_branding_page_shows_all_branding_pool_options(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_email_branding_pool,
    default_email_branding,
    expected_branding_options,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            email_branding_id=default_email_branding,
        ),
    )

    mocker.patch(
        "app.email_branding_client.get_email_branding",
        return_value={
            "email_branding": {
                "logo": "logo2.png",
                "name": "Email branding name 2",
                "text": "org 2 branding text",
                "id": "email-branding-2-id",
                "colour": None,
                "brand_type": "org",
            }
        },
    )
    client_request.login(platform_admin_user)

    page = client_request.get(".organisation_email_branding", org_id=organisation_one["id"])

    assert page.select_one("h1").text == "Email branding"
    assert {normalize_spaces(heading.text) for heading in page.select(".govuk-heading-s")} == expected_branding_options

    add_options_button = page.select(".govuk-button--secondary")[-1]
    assert normalize_spaces(add_options_button.text) == "Add branding options"
    assert add_options_button.attrs["href"] == url_for(
        ".add_organisation_email_branding_options", org_id=organisation_one["id"]
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_organisation_email_branding_page_shows_remove_brand_links(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_email_branding_pool,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            email_branding_id=None,
        ),
    )

    mocker.patch(
        "app.email_branding_client.get_email_branding",
        return_value={
            "email_branding": {
                "logo": "logo2.png",
                "name": "Email branding name 2",
                "text": "org 2 branding text",
                "id": "email-branding-2-id",
                "colour": None,
                "brand_type": "org",
            }
        },
    )
    client_request.login(platform_admin_user)

    page = client_request.get(".organisation_email_branding", org_id=organisation_one["id"])

    headers_and_remove_links = page.select("h2.govuk-heading-s, .govuk-\\!-text-align-right a")
    assert [(element.name, normalize_spaces(element.text)) for element in headers_and_remove_links] == [
        ("h2", "GOV.UK (default)"),
        ("h2", "Email branding name 1"),
        ("a", "Remove this branding option"),
        ("h2", "Email branding name 2"),
        ("a", "Remove this branding option"),
    ]

    assert (
        headers_and_remove_links[2].get("href") == "/organisations/c011fa40-4cbe-4524-b415-dde2f421bd9c"
        "/settings/email-branding?remove_branding_id=email-branding-1-id"
    )

    assert (
        headers_and_remove_links[4].get("href") == "/organisations/c011fa40-4cbe-4524-b415-dde2f421bd9c"
        "/settings/email-branding?remove_branding_id=email-branding-2-id"
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_get_organisation_email_branding_page_with_remove_param(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_email_branding_pool,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            email_branding_id=None,
        ),
    )

    client_request.login(platform_admin_user)

    page = client_request.get(
        ".organisation_email_branding",
        org_id=organisation_one["id"],
        remove_branding_id="email-branding-1-id",
    )

    assert "Are you sure you want to remove ‘Email branding name 1’ branding?" in page.text
    assert normalize_spaces(page.select_one(".banner-dangerous form button").text) == "Yes, remove"


def test_post_organisation_email_branding_page_with_remove_param(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_email_branding_pool,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            email_branding_id=None,
        ),
    )
    remove_mock = mocker.patch("app.organisations_client.remove_email_branding_from_pool", return_value=None)

    client_request.login(platform_admin_user)

    response = client_request.post_response(
        ".organisation_email_branding",
        org_id=organisation_one["id"],
        remove_branding_id="email-branding-1-id",
    )

    assert remove_mock.call_args_list == [mocker.call("c011fa40-4cbe-4524-b415-dde2f421bd9c", "email-branding-1-id")]

    page = client_request.get_url(response.location)
    assert "Email branding ‘Email branding name 1’ removed." in page.text


def test_remove_org_email_branding_from_pool_invalid_brand_id(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_email_branding_pool,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            email_branding_id=None,
        ),
    )
    remove_mock = mocker.patch("app.organisations_client.remove_email_branding_from_pool", return_value=None)

    client_request.login(platform_admin_user)

    client_request.post(
        ".organisation_email_branding",
        org_id=organisation_one["id"],
        remove_branding_id="bad-email-branding-id",
        _expected_status=400,
    )

    assert remove_mock.call_args_list == []


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "organisation_type, should_be_available",
    (
        (Organisation.TYPE_CENTRAL, True),
        (Organisation.TYPE_LOCAL, False),
        (Organisation.TYPE_NHS_CENTRAL, False),
        (Organisation.TYPE_NHS_LOCAL, False),
        (Organisation.TYPE_NHS_GP, False),
        (Organisation.TYPE_EMERGENCY_SERVICE, False),
        (Organisation.TYPE_SCHOOL_OR_COLLEGE, False),
        (Organisation.TYPE_OTHER, False),
    ),
)
def test_reset_org_email_branding_to_govuk_only_for_central_government(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_email_branding_pool,
    organisation_type,
    should_be_available,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            email_branding_id="email-branding-1-id",
            organisation_type=organisation_type,
        ),
    )
    mocker.patch(
        "app.email_branding_client.get_email_branding",
        return_value={
            "email_branding": {
                "logo": "logo2.png",
                "name": "Email branding name 2",
                "text": "org 2 branding text",
                "id": "email-branding-2-id",
                "colour": None,
                "brand_type": "org",
            }
        },
    )

    client_request.login(platform_admin_user)

    url = url_for(".organisation_email_branding", org_id=organisation_one["id"]) + "?change_default_branding_to_govuk"
    page = client_request.get_url(url)

    assert ("Use GOV.UK as default instead" in page.text) is should_be_available
    assert ("Are you sure you want to make GOV.UK the default email branding?" in page.text) is should_be_available


@pytest.mark.parametrize(
    "organisation_type, should_succeed",
    (
        (Organisation.TYPE_CENTRAL, True),
        (Organisation.TYPE_LOCAL, False),
        (Organisation.TYPE_NHS_CENTRAL, False),
        (Organisation.TYPE_NHS_LOCAL, False),
        (Organisation.TYPE_NHS_GP, False),
        (Organisation.TYPE_EMERGENCY_SERVICE, False),
        (Organisation.TYPE_SCHOOL_OR_COLLEGE, False),
        (Organisation.TYPE_OTHER, False),
    ),
)
def test_reset_org_email_branding_to_govuk_successfully(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_email_branding_pool,
    mock_update_organisation,
    organisation_type,
    should_succeed,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            email_branding_id=None,
            organisation_type=organisation_type,
        ),
    )
    expected_status = 302 if should_succeed else 200

    client_request.login(platform_admin_user)

    url = url_for(".organisation_email_branding", org_id=organisation_one["id"]) + "?change_default_branding_to_govuk"
    client_request.post_url(url, _expected_status=expected_status)

    expected_calls = []
    if should_succeed:
        expected_calls.append(mocker.call(organisation_one["id"], cached_service_ids=None, email_branding_id=None))

    assert mock_update_organisation.call_args_list == expected_calls


def test_change_default_org_email_branding_invalid_brand_id(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_email_branding_pool,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            email_branding_id=None,
        ),
    )

    client_request.login(platform_admin_user)

    client_request.post(
        ".organisation_email_branding",
        org_id=organisation_one["id"],
        new_default_branding_id="bad-email-branding-id",
        _expected_status=400,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_change_default_org_email_branding_shows_confirmation_question_from_govuk(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_email_branding_pool,
    mock_update_organisation,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            email_branding_id=None,
        ),
    )

    client_request.login(platform_admin_user)

    page = client_request.post(
        ".organisation_email_branding",
        org_id=organisation_one["id"],
        _data={"email_branding_id": "email-branding-1-id"},
        _follow_redirects=True,
    )

    assert "Are you sure you want to make ‘Email branding name 1’ the default email branding?" in page.text
    assert mock_update_organisation.call_args_list == []


def test_change_default_org_email_branding_successfully_from_govuk(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_email_branding_pool,
    mock_get_organisation_services,
    mock_update_organisation,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            email_branding_id=None,
        ),
    )

    client_request.login(platform_admin_user)

    client_request.post(
        ".organisation_email_branding",
        org_id=organisation_one["id"],
        new_default_branding_id="email-branding-1-id",
    )

    assert mock_update_organisation.call_args_list == [
        mocker.call(
            organisation_one["id"],
            cached_service_ids=["12345", "67890", SERVICE_ONE_ID],
            email_branding_id="email-branding-1-id",
        )
    ]


def test_change_default_org_email_branding_successfully_from_explicit_brand(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_email_branding_pool,
    mock_update_organisation,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            email_branding_id="email-branding-2-id",
        ),
    )

    mocker.patch(
        "app.email_branding_client.get_email_branding",
        return_value={
            "email_branding": {
                "logo": "logo2.png",
                "name": "Email branding name 2",
                "text": "org 2 branding text",
                "id": "email-branding-2-id",
                "colour": None,
                "brand_type": "org",
            }
        },
    )

    client_request.login(platform_admin_user)

    client_request.post(
        ".organisation_email_branding",
        org_id=organisation_one["id"],
        _data={"email_branding_id": "email-branding-1-id"},
    )

    assert mock_update_organisation.call_args_list == [
        mocker.call(organisation_one["id"], cached_service_ids=None, email_branding_id="email-branding-1-id")
    ]


def test_add_organisation_email_branding_options_is_platform_admin_only(
    client_request,
    organisation_one,
    mock_get_organisation,
    mocker,
):
    client_request.get(
        "main.add_organisation_email_branding_options", org_id=organisation_one["id"], _expected_status=403
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_add_organisation_email_branding_options_shows_branding_not_in_branding_pool(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
    mock_get_all_email_branding,
    mocker,
):
    branding_pool = [
        {
            "logo": "logo1.png",
            "name": "org 1",
            "text": "org 1",
            "id": "1",
            "colour": None,
            "brand_type": "org",
        },
        {
            "logo": "logo3.png",
            "name": "org 3",
            "text": None,
            "id": "3",
            "colour": None,
            "brand_type": "org",
        },
    ]
    mocker.patch("app.models.branding.EmailBrandingPool._get_items", return_value=branding_pool)

    client_request.login(platform_admin_user)
    page = client_request.get(".add_organisation_email_branding_options", org_id=organisation_one["id"])
    assert page.select_one("h1").text == "Add email branding options"
    assert page.select_one("[data-notify-module=live-search]")["data-targets"] == ".govuk-checkboxes__item"

    assert [
        (checkbox.text.strip(), checkbox.input["value"], checkbox.input.has_attr("checked"))
        for checkbox in page.select(".govuk-checkboxes__item")
    ] == [
        ("org 2", "2", False),
        ("org 4", "4", False),
        ("org 5", "5", False),
    ]
    assert normalize_spaces(page.select_one(".page-footer__button").text) == "Add selected options"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_add_organisation_email_branding_options_shows_error_if_no_branding_selected(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
    mock_get_all_email_branding,
    mock_get_email_branding_pool,
):
    client_request.login(platform_admin_user)
    page = client_request.post(
        ".add_organisation_email_branding_options",
        org_id=organisation_one["id"],
        _data=[],
        _expected_status=200,
    )
    assert (
        normalize_spaces(page.select_one(".govuk-error-message").text)
        == "Error: Select at least 1 email branding option"
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "branding_ids_added, flash_message",
    [
        (["1", "2"], "2 email branding options added"),
        (["1"], "1 email branding option added"),
    ],
)
def test_add_organisation_email_branding_options_calls_api_client_with_chosen_branding(
    client_request,
    platform_admin_user,
    organisation_one,
    mocker,
    mock_get_organisation,
    mock_get_all_email_branding,
    mock_get_email_branding_pool,
    branding_ids_added,
    flash_message,
):
    mock_update_pool = mocker.patch("app.organisations_client.add_brandings_to_email_branding_pool")

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".add_organisation_email_branding_options",
        org_id=organisation_one["id"],
        _data={"branding_field": branding_ids_added},
        _follow_redirects=True,
    )

    assert page.select_one("h1").text == "Email branding"
    assert normalize_spaces(page.select_one("div.banner-default-with-tick").text) == flash_message
    mock_update_pool.assert_called_once_with(organisation_one["id"], branding_ids_added)


def test_organisation_letter_branding_is_platform_admin_only(client_request, organisation_one, mock_get_organisation):
    client_request.get("main.organisation_letter_branding", org_id=organisation_one["id"], _expected_status=403)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_organisation_letter_branding_page_shows_all_branding_pool_options(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
    mock_get_letter_branding_pool,
):
    client_request.login(platform_admin_user)
    page = client_request.get("main.organisation_letter_branding", org_id=organisation_one["id"])

    assert page.select_one("h1").text == "Letter branding"
    assert [normalize_spaces(heading.text) for heading in page.select(".govuk-heading-s")] == [
        "No branding (default)",
        "Cabinet Office",
        "Department for Education",
        "Government Digital Service",
    ]

    assert "Use no branding as default instead" not in page.text

    add_options_button = page.select(".govuk-button--secondary")[-1]
    assert normalize_spaces(add_options_button.text) == "Add branding options"
    assert add_options_button.attrs["href"] == url_for(
        ".add_organisation_letter_branding_options", org_id=organisation_one["id"]
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_organisation_letter_branding_page_shows_remove_links(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_letter_branding_pool,
    mocker,
):
    organisation_one["letter_branding_id"] = "9abc"
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    mocker.patch(
        "app.models.branding.letter_branding_client.get_letter_branding",
        return_value={
            "id": "9abc",
            "name": "Government Digital Service",
            "filename": "gds",
        },
    )

    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_letter_branding", org_id=organisation_one["id"])

    headers_and_remove_links = page.select("h2.govuk-heading-s, .govuk-\\!-text-align-right a")
    assert [(element.name, normalize_spaces(element.text)) for element in headers_and_remove_links] == [
        ("h2", "Government Digital Service (default)"),
        ("h2", "Cabinet Office"),
        ("a", "Remove this branding option"),
        ("h2", "Department for Education"),
        ("a", "Remove this branding option"),
    ]

    assert headers_and_remove_links[2].get("href") == url_for(
        ".organisation_letter_branding", org_id=organisation_one["id"], remove_branding_id="1234"
    )
    assert headers_and_remove_links[4].get("href") == url_for(
        ".organisation_letter_branding", org_id=organisation_one["id"], remove_branding_id="5678"
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_get_organisation_letter_branding_page_with_remove_param_shows_confirmation(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_letter_branding_pool,
    mock_get_organisation,
):
    client_request.login(platform_admin_user)

    page = client_request.get(
        ".organisation_letter_branding",
        org_id=organisation_one["id"],
        remove_branding_id="1234",
    )

    assert "Are you sure you want to remove ‘Cabinet Office’ branding?" in page.text
    assert normalize_spaces(page.select_one(".banner-dangerous form button").text) == "Yes, remove"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_post_organisation_letter_branding_page_with_remove_param_calls_client_and_redirects(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_letter_branding_pool,
    mock_get_organisation,
    mocker,
):
    remove_mock = mocker.patch("app.organisations_client.remove_letter_branding_from_pool")

    client_request.login(platform_admin_user)

    page = client_request.post(
        ".organisation_letter_branding",
        org_id=organisation_one["id"],
        remove_branding_id="1234",
        _follow_redirects=True,
    )

    assert remove_mock.call_args_list == [mocker.call(ORGANISATION_ID, "1234")]

    assert page.select_one("h1").text == "Letter branding"
    assert "Letter branding ‘Cabinet Office’ removed." in page.text


def test_organisation_letter_branding_page_with_remove_param_when_branding_is_not_in_pool(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_letter_branding_pool,
    mock_get_organisation,
    fake_uuid,
):
    client_request.login(platform_admin_user)

    client_request.post(
        ".organisation_letter_branding",
        org_id=organisation_one["id"],
        remove_branding_id=fake_uuid,
        _expected_status=400,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_organisation_letter_branding_page_shows_confirmation_when_making_none_default(
    platform_admin_user,
    client_request,
    organisation_one,
    mock_get_letter_branding_pool,
    mocker,
):
    organisation_one["letter_branding_id"] = "9abc"
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    mocker.patch(
        "app.models.branding.letter_branding_client.get_letter_branding",
        return_value={
            "id": "9abc",
            "name": "Government Digital Service",
            "filename": "gds",
        },
    )

    client_request.login(platform_admin_user)

    url = url_for(".organisation_letter_branding", org_id=organisation_one["id"]) + "?change_default_branding_to_none"
    page = client_request.get_url(url)

    assert "Use no branding as default instead" in page.text
    assert normalize_spaces(page.select_one(".banner-title").text) == (
        "Are you sure you want to remove the default letter branding?"
    )


def test_organisation_letter_branding_page_makes_none_default_on_post_request(
    platform_admin_user,
    client_request,
    organisation_one,
    mock_get_organisation,
    mocker,
):
    update_mock = mocker.patch("app.organisations_client.update_organisation")

    client_request.login(platform_admin_user)

    url = url_for(".organisation_letter_branding", org_id=organisation_one["id"]) + "?change_default_branding_to_none"
    client_request.post_url(url)

    update_mock.assert_called_once_with(organisation_one["id"], cached_service_ids=None, letter_branding_id=None)


def test_add_organisation_letter_branding_options_is_platform_admin_only(
    client_request,
    organisation_one,
    mock_get_organisation,
):
    client_request.get(
        "main.add_organisation_letter_branding_options", org_id=organisation_one["id"], _expected_status=403
    )


def test_change_default_org_letter_branding_invalid_brand_id(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_letter_branding_pool,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            letter_branding_id=None,
        ),
    )

    client_request.login(platform_admin_user)

    client_request.post(
        ".organisation_letter_branding",
        org_id=organisation_one["id"],
        new_default_branding_id="bad-letter-branding-id",
        _expected_status=400,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_change_default_org_letter_branding_shows_confirmation_question_when_changing_from_no_branding(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_letter_branding_pool,
    mock_update_organisation,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            letter_branding_id=None,
        ),
    )

    client_request.login(platform_admin_user)

    page = client_request.post(
        ".organisation_letter_branding",
        org_id=organisation_one["id"],
        _data={"letter_branding_id": "1234"},
        _follow_redirects=True,
    )

    assert "Are you sure you want to make ‘Cabinet Office’ the default letter branding?" in page.text
    assert not mock_update_organisation.called


def test_change_default_org_letter_branding_successfully_from_no_branding(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_letter_branding_pool,
    mock_get_organisation_services,
    mock_update_organisation,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            letter_branding_id=None,
        ),
    )

    client_request.login(platform_admin_user)

    client_request.post(
        ".organisation_letter_branding",
        org_id=organisation_one["id"],
        new_default_branding_id="1234",
    )

    assert mock_update_organisation.call_args_list == [
        mocker.call(
            organisation_one["id"], cached_service_ids=["12345", "67890", SERVICE_ONE_ID], letter_branding_id="1234"
        )
    ]


def test_change_default_org_letter_branding_successfully_from_explicit_brand(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_letter_branding_pool,
    mock_update_organisation,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            letter_branding_id="1234",
        ),
    )

    client_request.login(platform_admin_user)

    client_request.post(
        ".organisation_letter_branding",
        org_id=organisation_one["id"],
        _data={"letter_branding_id": "5678"},
    )

    assert mock_update_organisation.call_args_list == [
        mocker.call(organisation_one["id"], cached_service_ids=None, letter_branding_id="5678")
    ]


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_add_organisation_letter_branding_options_shows_branding_not_in_branding_pool(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
    mock_get_letter_branding_pool,
    mocker,
):
    # The first 3 items in all_letter_branding are in the pool, the last 2 are not
    all_letter_branding = [
        {
            "id": "1234",
            "name": "Cabinet Office",
            "filename": "co",
        },
        {
            "id": "5678",
            "name": "Department for Education",
            "filename": "dfe",
        },
        {
            "id": "9abc",
            "name": "Government Digital Service",
            "filename": "gds",
        },
        {
            "id": "abcd",
            "name": "Land Registry",
            "filename": "land-registry",
        },
        {
            "id": "efgh",
            "name": "Animal and Plant Health Agency",
            "filename": "apha",
        },
    ]
    mocker.patch("app.models.branding.AllLetterBranding._get_items", return_value=all_letter_branding)

    client_request.login(platform_admin_user)
    page = client_request.get(".add_organisation_letter_branding_options", org_id=organisation_one["id"])
    assert page.select_one("h1").text == "Add letter branding options"
    assert page.select_one("[data-notify-module=live-search]")["data-targets"] == ".govuk-checkboxes__item"

    assert [
        (checkbox.text.strip(), checkbox.input["value"], checkbox.input.has_attr("checked"))
        for checkbox in page.select(".govuk-checkboxes__item")
    ] == [
        ("Animal and Plant Health Agency", "efgh", False),
        ("Land Registry", "abcd", False),
    ]
    assert normalize_spaces(page.select_one(".page-footer__button").text) == "Add selected options"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_add_organisation_letter_branding_options_shows_error_if_no_branding_selected(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
    mock_get_all_letter_branding,
    mock_get_letter_branding_pool,
):
    client_request.login(platform_admin_user)
    page = client_request.post(
        ".add_organisation_letter_branding_options",
        org_id=organisation_one["id"],
        _data=[],
        _expected_status=200,
    )
    assert (
        normalize_spaces(page.select_one(".govuk-error-message").text)
        == "Error: Select at least 1 letter branding option"
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "branding_ids_added, flash_message",
    [
        ([str(UUID(int=0)), str(UUID(int=1))], "2 letter branding options added"),
        ([str(UUID(int=0))], "1 letter branding option added"),
    ],
)
def test_add_organisation_letter_branding_options_calls_api_client_with_chosen_branding(
    client_request,
    platform_admin_user,
    organisation_one,
    mocker,
    mock_get_organisation,
    mock_get_all_letter_branding,
    mock_get_letter_branding_pool,
    branding_ids_added,
    flash_message,
):
    mock_update_pool = mocker.patch("app.organisations_client.add_brandings_to_letter_branding_pool")

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".add_organisation_letter_branding_options",
        org_id=organisation_one["id"],
        _data={"branding_field": branding_ids_added},
        _follow_redirects=True,
    )

    assert page.select_one("h1").text == "Letter branding"
    assert normalize_spaces(page.select_one("div.banner-default-with-tick").text) == flash_message
    mock_update_pool.assert_called_once_with(organisation_one["id"], branding_ids_added)

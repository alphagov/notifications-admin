from io import BytesIO
from textwrap import dedent
from unittest import mock
from unittest.mock import ANY, PropertyMock
from urllib.parse import parse_qs, urlparse

import pytest
from flask import url_for
from notifications_utils.clients.zendesk.zendesk_client import NotifySupportTicket

from app.models.branding import EmailBranding
from tests import sample_uuid
from tests.conftest import (
    ORGANISATION_ID,
    SERVICE_ONE_ID,
    create_email_branding,
    create_email_branding_pool,
    create_email_brandings,
    normalize_spaces,
)
from tests.utils import ComparablePropertyMock


def test_email_branding_options_page_back_link(
    client_request, mock_get_email_branding_pool, service_one, organisation_one, mocker
):
    organisation_one["organisation_type"] = "central"
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    page = client_request.get(".email_branding_options", service_id=SERVICE_ONE_ID)

    back_link = page.select("a[class=govuk-back-link]")
    assert back_link[0].attrs["href"] == url_for(".service_settings", service_id=SERVICE_ONE_ID)


def test_email_branding_options_page_shows_branding_if_set(
    mocker,
    service_one,
    client_request,
    mock_get_empty_email_branding_pool,
    mock_get_email_branding,
    mock_get_service_organisation,
):
    mocker.patch(
        "app.models.service.Service.email_branding_id",
        new_callable=PropertyMock,
        return_value="some-random-branding",
    )

    page = client_request.get(".email_branding_options", service_id=SERVICE_ONE_ID)
    assert page.select_one("iframe")["src"] == url_for("main.email_template", branding_style="some-random-branding")


def test_email_branding_options_page_when_no_branding_is_set(
    service_one,
    client_request,
    mocker,
    mock_get_empty_email_branding_pool,
    mock_get_email_branding,
    mock_get_letter_branding_by_id,
):
    service_one["email_branding"] = None
    service_one["organisation_type"] = "nhs_central"

    mocker.patch(
        "app.models.service.Service.email_branding_id",
        new_callable=PropertyMock,
        return_value=None,
    )

    page = client_request.get(
        ".email_branding_options",
        service_id=SERVICE_ONE_ID,
    )

    assert mock_get_email_branding.called is False
    assert page.select_one("iframe")["src"] == url_for("main.email_template", branding_style="__NONE__")
    assert mock_get_letter_branding_by_id.called is False

    button_text = normalize_spaces(page.select_one(".page-footer button").text)

    assert [
        (radio["value"], page.select_one("label[for={}]".format(radio["id"])).text.strip())
        for radio in page.select("input[type=radio]")
    ] == [(EmailBranding.NHS_ID, "NHS"), ("something_else", "Something else")]

    assert button_text == "Continue"


@pytest.mark.parametrize(
    "organisation_type, expected_options",
    (
        (
            "nhs_central",
            [
                (EmailBranding.NHS_ID, "NHS"),
                ("email-branding-1-id", "Email branding name 1"),
                ("email-branding-2-id", "Email branding name 2"),
                ("something_else", "Something else"),
            ],
        ),
        (
            "central",
            [
                ("govuk", "GOV.UK"),
                ("govuk_and_org", "GOV.UK and organisation one"),
                ("email-branding-1-id", "Email branding name 1"),
                ("email-branding-2-id", "Email branding name 2"),
                ("something_else", "Something else"),
            ],
        ),
        (
            "other",
            [
                ("email-branding-1-id", "Email branding name 1"),
                ("email-branding-2-id", "Email branding name 2"),
                ("something_else", "Something else"),
            ],
        ),
    ),
)
def test_email_branding_options_page_shows_branding_pool_options_if_branding_pool_set_for_org(
    mocker,
    service_one,
    organisation_one,
    client_request,
    mock_get_email_branding,
    mock_get_email_branding_pool,
    organisation_type,
    expected_options,
):

    service_one["organisation_type"] = organisation_type
    organisation_one["organisation_type"] = organisation_type
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    mocker.patch(
        "app.models.service.Service.email_branding_id",
        new_callable=PropertyMock,
        return_value="some-random-branding",
    )

    page = client_request.get(".email_branding_options", service_id=SERVICE_ONE_ID)

    assert [
        (radio["value"], page.select_one("label[for={}]".format(radio["id"])).text.strip())
        for radio in page.select("input[type=radio]")
    ] == expected_options


@pytest.mark.parametrize(
    "pool_contents, expected_options",
    (
        (
            [],
            [
                ("govuk-radios__item", "GOV.UK and organisation one"),
                ("govuk-radios__item", "organisation one"),
                ("govuk-radios__item", "Something else"),
            ],
        ),
        (
            create_email_branding_pool(),
            [
                ("govuk-radios__item", "GOV.UK and organisation one"),
                ("govuk-radios__item", "Email branding name 1"),
                ("govuk-radios__item", "Email branding name 2"),
                ("govuk-radios__divider", "or"),
                ("govuk-radios__item", "Something else"),
            ],
        ),
    ),
)
def test_email_branding_options_page_shows_divider_if_there_are_lots_of_options(
    mocker,
    service_one,
    organisation_one,
    client_request,
    mock_get_email_branding,
    mock_get_email_branding_pool,
    pool_contents,
    expected_options,
):
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    mocker.patch(
        "app.models.branding.EmailBrandingPool.client_method",
        return_value=pool_contents,
    )

    page = client_request.get(".email_branding_options", service_id=SERVICE_ONE_ID)

    assert [
        (item["class"][0], normalize_spaces(item))
        for item in page.select(".govuk-radios__item, .govuk-radios__divider")
    ] == expected_options


def test_email_branding_options_does_not_show_nhs_branding_twice(
    mocker,
    service_one,
    organisation_one,
    client_request,
    mock_get_email_branding,
):
    organisation_one["organisation_type"] = "nhs_central"
    service_one["organisation"] = organisation_one

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    nhs_branding = create_email_branding(EmailBranding.NHS_ID, {"colour": None, "name": "NHS", "text": None})[
        "email_branding"
    ]
    updated_branding_pool = create_email_branding_pool(additional_values=nhs_branding)
    mocker.patch("app.models.branding.EmailBrandingPool.client_method", return_value=updated_branding_pool)

    page = client_request.get(".email_branding_options", service_id=SERVICE_ONE_ID)

    assert [
        (radio["value"], page.select_one(f'label[for={radio["id"]}]').text.strip())
        for radio in page.select("input[type=radio]")
    ] == [
        (EmailBranding.NHS_ID, "NHS"),
        ("email-branding-1-id", "Email branding name 1"),
        ("email-branding-2-id", "Email branding name 2"),
        ("something_else", "Something else"),
    ]


def test_email_branding_options_page_shows_preview_if_something_else_is_only_option(
    mocker,
    service_one,
    client_request,
    mock_get_email_branding,
    mock_get_empty_email_branding_pool,
):
    service_one["organisation_type"] = "other"
    mocker.patch(
        "app.models.service.Service.email_branding_id",
        new_callable=PropertyMock,
        return_value="some-random-branding",
    )

    page = client_request.get(
        ".email_branding_options",
        service_id=SERVICE_ONE_ID,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Change email branding"
    assert page.select("iframe.branding-preview")
    assert not page.select("input[type=radio]")
    assert normalize_spaces(page.select_one("form[method=post] button").text) == "Continue"


@pytest.mark.parametrize(
    "data, org_type, endpoint, extra_args",
    (
        (
            {"options": "govuk"},
            "central",
            "main.email_branding_govuk",
            {},
        ),
        (
            {"options": "govuk_and_org"},
            "central",
            "main.email_branding_choose_logo",
            {"branding_choice": "govuk_and_org"},
        ),
        (
            {"options": "organisation"},
            "central",
            "main.email_branding_choose_logo",
            {"branding_choice": "organisation"},
        ),
        (
            {"options": "something_else"},
            "central",
            "main.email_branding_choose_logo",
            {"branding_choice": "something_else"},
        ),
        (
            {"options": "something_else"},
            "local",
            "main.email_branding_choose_banner_type",
            {"back_link": ".email_branding_options", "branding_choice": "something_else"},
        ),
        (
            {"options": "organisation"},
            "local",
            "main.email_branding_choose_banner_type",
            {"back_link": ".email_branding_options", "branding_choice": "organisation"},
        ),
        (
            {"options": EmailBranding.NHS_ID},
            "nhs_local",
            "main.email_branding_nhs",
            {},
        ),
    ),
)
def test_email_branding_options_submit(
    client_request,
    service_one,
    mocker,
    mock_get_empty_email_branding_pool,
    mock_get_email_branding,
    organisation_one,
    data,
    org_type,
    endpoint,
    extra_args,
):
    organisation_one["organisation_type"] = org_type
    service_one["email_branding"] = sample_uuid()
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    client_request.post(
        ".email_branding_options",
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=302,
        _expected_redirect=url_for(
            endpoint,
            service_id=SERVICE_ONE_ID,
            **extra_args,
        ),
    )


def test_email_branding_options_submit_when_no_radio_button_is_selected(
    client_request,
    service_one,
    mock_get_empty_email_branding_pool,
    mock_get_email_branding,
):
    service_one["email_branding"] = sample_uuid()

    page = client_request.post(
        ".email_branding_options",
        service_id=SERVICE_ONE_ID,
        _data={"options": ""},
        _follow_redirects=True,
    )
    assert page.select_one("h1").text == "Change email branding"
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == "Error: Select an option"


def test_email_branding_options_page_redirects_to_choose_banner_type_page_if_something_else_is_only_option(
    mocker,
    service_one,
    client_request,
    mock_get_email_branding,
    mock_get_empty_email_branding_pool,
):
    service_one["organisation_type"] = "other"
    mocker.patch(
        "app.models.service.Service.email_branding_id",
        new_callable=PropertyMock,
        return_value="some-random-branding",
    )

    client_request.post(
        ".email_branding_options",
        service_id=SERVICE_ONE_ID,
        _data={"options": "something_else"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.email_branding_choose_banner_type",
            service_id=SERVICE_ONE_ID,
            branding_choice="something_else",
            back_link=".email_branding_options",
        ),
    )


def test_email_branding_options_page_redirects_nhs_specific_page(
    mocker,
    service_one,
    client_request,
    organisation_one,
):
    service_one["organisation"] = organisation_one["id"]
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    mocker.patch(
        "app.models.branding.EmailBrandingPool.client_method",
        return_value=[
            {
                "name": "NHS",
                "id": EmailBranding.NHS_ID,
            },
        ],
    )

    client_request.post(
        ".email_branding_options",
        service_id=SERVICE_ONE_ID,
        _data={"options": EmailBranding.NHS_ID},
        _expected_redirect=url_for(
            "main.email_branding_nhs",
            service_id=SERVICE_ONE_ID,
        ),
    )


def test_email_branding_options_redirects_to_branding_preview_for_a_branding_pool_option(
    mocker, service_one, organisation_one, client_request, mock_get_email_branding, mock_get_email_branding_pool
):
    organisation_one["organisation_type"] = "central"
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    mocker.patch(
        "app.models.service.Service.email_branding_id",
        new_callable=PropertyMock,
        return_value="some-random-branding",
    )

    client_request.post(
        ".email_branding_options",
        service_id=SERVICE_ONE_ID,
        _data={"options": "email-branding-1-id"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.email_branding_option_preview",
            service_id=SERVICE_ONE_ID,
            branding_option="email-branding-1-id",
        ),
    )


def test_email_branding_option_preview_page_displays_preview_of_chosen_branding(
    service_one, organisation_one, client_request, mocker, mock_get_email_branding_pool
):
    organisation_one["organisation_type"] = "central"
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    page = client_request.get(
        ".email_branding_option_preview", service_id=SERVICE_ONE_ID, branding_option="email-branding-1-id"
    )

    assert page.select_one("iframe")["src"] == url_for("main.email_template", branding_style="email-branding-1-id")


def test_email_branding_option_preview_page_redirects_to_branding_request_page_if_branding_option_not_found(
    service_one, organisation_one, client_request, mocker, mock_get_email_branding_pool
):
    organisation_one["organisation_type"] = "central"
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    client_request.get(
        ".email_branding_option_preview",
        service_id=SERVICE_ONE_ID,
        branding_option="some-unknown-branding-id",
        _expected_status=302,
        _expected_redirect=url_for("main.email_branding_options", service_id=SERVICE_ONE_ID),
    )


def test_email_branding_option_preview_changes_email_branding_when_user_confirms(
    mocker,
    service_one,
    organisation_one,
    client_request,
    no_reply_to_email_addresses,
    single_sms_sender,
    mock_get_email_branding_pool,
    mock_update_service,
):
    organisation_one["organisation_type"] = "central"
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    page = client_request.post(
        ".email_branding_option_preview",
        service_id=SERVICE_ONE_ID,
        branding_option="email-branding-1-id",
        _follow_redirects=True,
    )

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        email_branding="email-branding-1-id",
    )
    assert page.select_one("h1").text == "Settings"
    assert normalize_spaces(page.select_one(".banner-default").text) == "You’ve updated your email branding"


@pytest.mark.parametrize(
    "endpoint, service_org_type, branding_preview_id",
    [
        ("main.email_branding_govuk", "central", "__NONE__"),
        ("main.email_branding_nhs", "nhs_local", EmailBranding.NHS_ID),
    ],
)
def test_email_branding_govuk_and_nhs_pages(
    client_request,
    mocker,
    service_one,
    organisation_one,
    mock_get_empty_email_branding_pool,
    mock_get_email_branding,
    endpoint,
    service_org_type,
    branding_preview_id,
):
    organisation_one["organisation_type"] = service_org_type
    service_one["email_branding"] = sample_uuid()
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
    )
    assert page.select_one("h1").text == "Check your new branding"
    assert "Emails from service one will look like this" in normalize_spaces(page.text)
    assert page.select_one("iframe")["src"] == url_for("main.email_template", branding_style=branding_preview_id)
    assert normalize_spaces(page.select_one(".page-footer button").text) == "Use this branding"


@pytest.mark.parametrize(
    "endpoint",
    [
        "main.email_branding_govuk",
        "main.email_branding_nhs",
    ],
)
def test_email_branding_pages_give_404_if_selected_branding_not_allowed(
    client_request,
    mock_get_empty_email_branding_pool,
    endpoint,
):
    # The only email branding allowed is 'something_else', so trying to visit any of the other
    # endpoints gives a 404 status code.
    client_request.get(endpoint, service_id=SERVICE_ONE_ID, _expected_status=404)


def test_email_branding_govuk_submit(
    mocker,
    client_request,
    service_one,
    organisation_one,
    no_reply_to_email_addresses,
    mock_get_empty_email_branding_pool,
    mock_get_email_branding,
    single_sms_sender,
    mock_update_service,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )
    mocker.patch(
        "app.models.service.Service.organisation_id",
        new_callable=PropertyMock,
        return_value=ORGANISATION_ID,
    )
    service_one["email_branding"] = sample_uuid()

    page = client_request.post(
        ".email_branding_govuk",
        service_id=SERVICE_ONE_ID,
        _follow_redirects=True,
    )

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        email_branding=None,
    )
    assert page.select_one("h1").text == "Settings"
    assert normalize_spaces(page.select_one(".banner-default").text) == "You’ve updated your email branding"


def test_email_branding_nhs_submit(
    mocker,
    client_request,
    service_one,
    organisation_one,
    no_reply_to_email_addresses,
    mock_get_empty_email_branding_pool,
    mock_get_email_branding,
    single_sms_sender,
    mock_update_service,
):
    service_one["email_branding"] = sample_uuid()
    service_one["organisation_type"] = "nhs_local"

    page = client_request.post(
        ".email_branding_nhs",
        service_id=SERVICE_ONE_ID,
        _follow_redirects=True,
    )

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        email_branding=EmailBranding.NHS_ID,
    )
    assert page.select_one("h1").text == "Settings"
    assert normalize_spaces(page.select_one(".banner-default").text) == "You’ve updated your email branding"


def test_email_branding_request_page(client_request, service_one, mock_get_empty_email_branding_pool):
    # expect to have a "NHS" option as well as the
    # fallback, so back button goes to choices page
    service_one["organisation_type"] = "nhs_central"

    page = client_request.get(
        "main.email_branding_request",
        service_id=SERVICE_ONE_ID,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Describe the branding you want"
    assert page.select_one("textarea")["name"] == "something_else"
    assert normalize_spaces(page.select_one(".page-footer button").text) == "Request new branding"
    assert page.select_one(".govuk-back-link")["href"] == url_for(
        "main.email_branding_options",
        service_id=SERVICE_ONE_ID,
    )


@pytest.mark.parametrize(
    "back_view, back_view_args",
    (
        (".email_branding_choose_banner_type", {}),
        (".email_branding_choose_banner_colour", {"brand_type": "org"}),
        (".email_branding_upload_logo", {"brand_type": "org", "colour": "1ce"}),
    ),
)
def test_email_branding_request_back_to_new_email_branding_query_params(
    client_request, service_one, mock_get_empty_email_branding_pool, back_view, back_view_args
):
    service_one["organisation_type"] = "nhs_central"

    page = client_request.get(
        "main.email_branding_request",
        service_id=SERVICE_ONE_ID,
        back_link=back_view,
        **back_view_args,
    )
    back_link = page.select_one(".govuk-back-link")
    assert back_link["href"] == url_for(back_view, service_id=SERVICE_ONE_ID, **back_view_args)


@pytest.mark.parametrize("back_link", [".service_settings", ".email_branding_options", ".email_branding_choose_logo"])
def test_email_branding_request_page_back_link_from_args(
    client_request, service_one, mock_get_empty_email_branding_pool, back_link
):
    # expect to have a "NHS" option as well as the
    # fallback, so "something else" is not an only option
    service_one["organisation_type"] = "nhs_central"

    page = client_request.get("main.email_branding_request", service_id=SERVICE_ONE_ID, back_link=back_link)
    assert normalize_spaces(page.select_one("h1").text) == "Describe the branding you want"
    assert page.select_one(".govuk-back-link")["href"] == url_for(
        back_link,
        service_id=SERVICE_ONE_ID,
    )


def test_get_email_branding_request_page_is_only_option(
    client_request, service_one, mock_get_empty_email_branding_pool
):
    # should only have a "something else" option
    # so back button goes back to settings page
    service_one["organisation_type"] = "other"

    page = client_request.get(
        "main.email_branding_request",
        service_id=SERVICE_ONE_ID,
    )
    assert page.select_one(".govuk-back-link")["href"] == url_for(
        "main.service_settings",
        service_id=SERVICE_ONE_ID,
    )


def test_email_branding_request_submit(
    client_request,
    mocker,
    service_one,
    no_reply_to_email_addresses,
    mock_get_empty_email_branding_pool,
    mock_get_email_branding,
    single_sms_sender,
):
    service_one["email_branding"] = sample_uuid()
    service_one["organisation_type"] = "nhs_local"

    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mock_send_ticket_to_zendesk = mocker.patch(
        "app.main.views.service_settings.index.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )

    page = client_request.post(
        ".email_branding_request",
        service_id=SERVICE_ONE_ID,
        _data={"something_else": "Homer Simpson"},
        _follow_redirects=True,
    )

    mock_create_ticket.assert_called_once_with(
        ANY,
        message="\n".join(
            [
                "Organisation: Can’t tell (domain is user.gov.uk)",
                "Service: service one",
                "http://localhost/services/596364a0-858e-42c8-9062-a8fe822260eb",
                "",
                "---",
                "Current branding: Organisation name",
                "Branding requested:\n",
                "Homer Simpson",
            ]
        ),
        subject="Email branding request - service one",
        ticket_type="question",
        user_name="Test User",
        user_email="test@user.gov.uk",
        org_id=None,
        org_type="nhs_local",
        service_id=SERVICE_ONE_ID,
    )
    mock_send_ticket_to_zendesk.assert_called_once()
    assert normalize_spaces(page.select_one(".banner-default").text) == (
        "Thanks for your branding request. We’ll get back to you within one working day."
    )


def test_email_branding_request_submit_shows_error_if_textbox_is_empty(
    client_request, mock_get_empty_email_branding_pool
):
    page = client_request.post(
        ".email_branding_request",
        service_id=SERVICE_ONE_ID,
        _data={"something_else": ""},
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Describe the branding you want"
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == "Error: Cannot be empty"


def test_GET_email_branding_enter_government_identity_logo_text(client_request, service_one):
    page = client_request.get("main.email_branding_enter_government_identity_logo_text", service_id=service_one["id"])

    back_button = page.select_one("a.govuk-back-link")
    form = page.select_one("form")
    submit_button = form.select_one("button")
    text_input = form.select_one("input")

    assert back_button["href"] == url_for(
        "main.email_branding_request_government_identity_logo", service_id=service_one["id"]
    )
    assert back_button.text.strip() == "Back"
    assert form["method"] == "post"
    assert "Request new branding" in submit_button.text
    assert text_input["name"] == "logo_text"


@pytest.mark.parametrize(
    "extra_brandings_to_create, expected_branding_id_in_iframe",
    (
        (
            [],
            None,
        ),
        (
            [{"idx": 3, "id": "dfe1234", "name": "Department for Education - National Apprenticeship Service"}],
            None,
        ),
        (
            [{"idx": 3, "id": "dfe1234", "name": "Department for EDUCATION"}],
            "dfe1234",
        ),
    ),
)
def test_email_branding_create_government_identity_logo(
    mocker,
    client_request,
    service_one,
    extra_brandings_to_create,
    expected_branding_id_in_iframe,
):
    mocker.patch(
        "app.models.branding.AllEmailBranding.client_method",
        return_value=create_email_brandings(5, non_standard_values=extra_brandings_to_create),
    )
    page = client_request.get("main.email_branding_request_government_identity_logo", service_id=service_one["id"])

    back_button = page.select_one("a.govuk-back-link")
    continue_button = page.select_one("main a.govuk-button")
    iframe = page.select_one("iframe")

    assert back_button["href"] == url_for(".email_branding_choose_logo", service_id=SERVICE_ONE_ID)
    assert continue_button["href"] == url_for(
        ".email_branding_enter_government_identity_logo_text",
        service_id=SERVICE_ONE_ID,
    )
    assert "Continue" in continue_button.text
    assert "Back" in back_button.text
    if expected_branding_id_in_iframe:
        assert iframe["src"] == url_for("main.email_template", branding_style=expected_branding_id_in_iframe)
    else:
        assert not iframe


def test_GET_email_branding_enter_government_identity_logo_text_protects_against_xss(
    client_request, service_one, organisation_one, mocker
):
    organisation_one["name"] = "<script>evil</script>"
    service_one["organisation"] = organisation_one["id"]
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    page = client_request.get("main.email_branding_enter_government_identity_logo_text", service_id=service_one["id"])

    hint = page.select_one("form .govuk-hint")
    assert not hint.select("script")
    assert organisation_one["name"] in normalize_spaces(hint.text)


@pytest.mark.parametrize(
    "extra_url_args,expected_ticket_content,expected_extra_url_args",
    [
        (
            {"branding_choice": "something-else"},
            """
        Organisation: Can’t tell (domain is user.gov.uk)
        Service: service one
        {service_dashboard}

        ---
        Government logo text requested: My lovely government identity

        Create this logo: {create_email_branding_government_identity_logo}

        Apply branding to this service: {service_set_branding}
    """,
            {},
        ),
        (
            {"branding_choice": "govuk_and_org"},
            """
        Organisation: Can’t tell (domain is user.gov.uk)
        Service: service one
        {service_dashboard}

        ---
        Government logo text requested: My lovely government identity

        This service requested for both GOV.UK and organisation logo to be visible.

        Create this logo: {create_email_branding_government_identity_logo}

        Apply branding to this service: {service_set_branding}
    """,
            {"brand_type": "both"},
        ),
        (
            {"branding_choice": "organisation"},
            """
        Organisation: Can’t tell (domain is user.gov.uk)
        Service: service one
        {service_dashboard}

        ---
        Government logo text requested: My lovely government identity

        This service requested organisation branding.

        Create this logo: {create_email_branding_government_identity_logo}

        Apply branding to this service: {service_set_branding}
    """,
            {},
        ),
    ],
)
def test_POST_email_branding_enter_government_identity_logo_text(
    mocker, client_request, service_one, extra_url_args, expected_ticket_content, expected_extra_url_args
):
    mock_send_ticket_to_zendesk = mocker.patch(
        "app.main.views.service_settings.index.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )
    mock_flash = mocker.patch("app.main.views.service_settings.email_branding.flash", autospec=True)

    client_request.post(
        "main.email_branding_enter_government_identity_logo_text",
        service_id=service_one["id"],
        _data={"logo_text": "My lovely government identity"},
        **extra_url_args,
    )

    assert "Thanks for your branding request." in mock_flash.call_args_list[0][0][0]
    assert mock_send_ticket_to_zendesk.call_count == 1
    assert (
        mock_send_ticket_to_zendesk.call_args[0][0].message
        == dedent(expected_ticket_content)
        .format(
            service_dashboard=url_for("main.service_dashboard", service_id=SERVICE_ONE_ID, _external=True),
            create_email_branding_government_identity_logo=url_for(
                "main.create_email_branding_government_identity_logo",
                text="My lovely government identity",
                _external=True,
                **expected_extra_url_args,
            ),
            service_set_branding=url_for(
                "main.service_set_branding", service_id=SERVICE_ONE_ID, notification_type="email", _external=True
            ),
        )
        .strip()
    )


def test_email_branding_choose_logo_page(client_request, service_one):
    page = client_request.get(
        "main.email_branding_choose_logo",
        service_id=SERVICE_ONE_ID,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Choose a logo for your emails"

    assert page.select_one(".govuk-back-link")["href"] == url_for(
        "main.email_branding_options",
        service_id=SERVICE_ONE_ID,
    )

    assert [
        (radio["value"], page.select_one(f"label.govuk-label[for=branding_options-{i}]").text.strip())
        for i, radio in enumerate(page.select("input[type=radio]"))
    ] == [
        ("single_identity", "Create a government identity logo"),
        ("org", "Upload a logo"),
    ]


@pytest.mark.parametrize(
    "branding_choice, expected_hint",
    (
        ("org", "Test organisation branding is not set up yet."),
        ("govuk_and_org", "GOV.UK and Test organisation branding is not set up yet."),
        ("something_else", ""),
        ("", ""),
    ),
)
def test_email_branding_choose_logo_page_shows_not_setup_message(
    client_request,
    service_one,
    fake_uuid,
    mock_get_organisation,
    branding_choice,
    expected_hint,
):
    service_one["organisation"] = fake_uuid
    page = client_request.get(
        "main.email_branding_choose_logo",
        service_id=SERVICE_ONE_ID,
        branding_choice=branding_choice,
    )

    hint = page.select_one("#branding_options-hint")

    if expected_hint:
        assert normalize_spaces(hint.text) == expected_hint
    else:
        assert not hint


def test_email_branding_choose_logo_page_prevents_xss_attacks(
    mocker,
    client_request,
    service_one,
    organisation_one,
):
    service_one["organisation"] = organisation_one
    organisation_one["name"] = "<script>evil</script>"
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    page = client_request.get(
        "main.email_branding_choose_logo",
        service_id=SERVICE_ONE_ID,
        branding_choice="org",
    )

    hint = page.select_one("form .govuk-hint")
    assert not hint.select_one("script")
    assert organisation_one["name"] in normalize_spaces(hint.text)


def test_only_central_org_services_can_see_email_branding_choose_logo_page(client_request, service_one):
    service_one["organisation_type"] = "local"

    client_request.get(
        "main.email_branding_choose_logo",
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
    )


@pytest.mark.parametrize(
    "branding_choice, selected_option, expected_endpoint, extra_url_args",
    [
        (
            "something_else",
            "org",
            ".email_branding_choose_banner_type",
            {"back_link": ".email_branding_choose_logo", "branding_choice": "something_else"},
        ),
        (
            "something_else",
            "single_identity",
            ".email_branding_request_government_identity_logo",
            {"branding_choice": "something_else"},
        ),
        (
            "org",
            "org",
            ".email_branding_choose_banner_type",
            {"back_link": ".email_branding_choose_logo", "branding_choice": "org"},
        ),
        ("org", "single_identity", ".email_branding_request_government_identity_logo", {"branding_choice": "org"}),
        (
            "govuk_and_org",
            "org",
            ".email_branding_upload_logo",
            {"back_link": ".email_branding_choose_logo", "branding_choice": "govuk_and_org", "brand_type": "both"},
        ),
        (
            "govuk_and_org",
            "single_identity",
            ".email_branding_request_government_identity_logo",
            {"branding_choice": "govuk_and_org"},
        ),
    ],
)
def test_email_branding_choose_logo_redirects_to_right_page(
    client_request, service_one, branding_choice, selected_option, expected_endpoint, extra_url_args
):
    client_request.post(
        ".email_branding_choose_logo",
        service_id=SERVICE_ONE_ID,
        branding_choice=branding_choice,
        _data={"branding_options": selected_option},
        _expected_status=302,
        _expected_redirect=url_for(expected_endpoint, service_id=SERVICE_ONE_ID, **extra_url_args),
    )


@pytest.mark.parametrize(
    "query_params, expected_back_link, expected_skip_link",
    (
        (
            {},
            "/services/596364a0-858e-42c8-9062-a8fe822260eb/service-settings/email-branding/add-banner",
            (
                "/services/596364a0-858e-42c8-9062-a8fe822260eb/service-settings/email-branding/request"
                "?back_link=.email_branding_upload_logo"
            ),
        ),
        (
            {"brand_type": "org"},
            "/services/596364a0-858e-42c8-9062-a8fe822260eb/service-settings/email-branding/add-banner",
            (
                "/services/596364a0-858e-42c8-9062-a8fe822260eb/service-settings/email-branding/request"
                "?back_link=.email_branding_upload_logo&brand_type=org"
            ),
        ),
        (
            {"brand_type": "org_banner"},
            "/services/596364a0-858e-42c8-9062-a8fe822260eb/service-settings/email-branding/choose-banner-colour?brand_type=org_banner",  # noqa
            (
                "/services/596364a0-858e-42c8-9062-a8fe822260eb/service-settings/email-branding/request"
                "?back_link=.email_branding_upload_logo&brand_type=org_banner"
            ),
        ),
    ),
)
def test_GET_email_branding_upload_logo(
    client_request, service_one, query_params, expected_back_link, expected_skip_link
):
    page = client_request.get(
        "main.email_branding_upload_logo",
        service_id=service_one["id"],
        **query_params,
    )

    back_button = page.select_one("a.govuk-back-link")
    form = page.select_one("form")
    submit_button = form.select_one("button")
    file_input = form.select_one("input")
    skip_link = page.select("main a")[-1]

    assert back_button["href"] == expected_back_link
    assert form["method"] == "post"
    assert "Submit" in submit_button.text
    assert file_input["name"] == "logo"

    assert skip_link is not None
    assert skip_link["href"] == expected_skip_link
    assert skip_link.text == "I do not have a file to upload"


@pytest.mark.parametrize(
    "email_branding_data",
    (
        {},
        {"brand_type": "org"},
        {"brand_type": "org_banner", "colour": "#abcdef"},
    ),
)
def test_POST_email_branding_upload_logo_success(mocker, client_request, service_one, email_branding_data):
    antivirus_mock = mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    mock_save_temporary = mocker.patch(
        "app.main.views.service_settings.email_branding.logo_client.save_temporary_logo", return_value="my-logo-path"
    )

    mocker.patch.dict(
        "flask.current_app.config", {"EMAIL_BRANDING_MIN_LOGO_HEIGHT_PX": 1, "EMAIL_BRANDING_MAX_LOGO_WIDTH_PX": 1}
    )

    client_request.post(
        "main.email_branding_upload_logo",
        _data={"logo": (open("tests/test_img_files/small-but-perfectly-formed.png", "rb"), "logo.png")},
        service_id=service_one["id"],
        **email_branding_data,
        _expected_redirect=url_for(
            "main.email_branding_set_alt_text",
            service_id=service_one["id"],
            **email_branding_data,
            logo="my-logo-path",
        ),
    )

    assert antivirus_mock.call_count == 1
    assert mock_save_temporary.call_args_list == [
        mocker.call(
            mocker.ANY,
            logo_type="email",
        )
    ]


@pytest.mark.parametrize(
    "post_data, expected_error",
    (
        (
            ({}, "You need to upload a file to submit"),
            ({"logo": (BytesIO(b""), "logo.svg")}, "Logo must be a PNG file"),
            (
                {"logo": (BytesIO(b"a" * 3 * 1024 * 1024), "logo.png")},
                "File must be smaller than 2MB",
            ),
            (
                lambda: {"logo": (open("tests/test_img_files/corrupt-magic-numbers.png", "rb"), "logo.png")},
                "Logo must be a PNG file",
            ),
            (
                lambda: {"logo": (open("tests/test_img_files/truncated.png", "rb"), "logo.png")},
                "Notify cannot read this file",
            ),
        )
    ),
)
def test_POST_email_branding_upload_logo_validation_errors(
    mocker, client_request, service_one, post_data, expected_error
):
    # File opens are wrapped in a lambda (we only want to do this during the test run, not when tests are gathered)
    if callable(post_data):
        post_data = post_data()

    mock_save_temporary = mocker.patch("app.main.views.service_settings.email_branding.logo_client.save_temporary_logo")

    with mock.patch.dict("app.main.validators.current_app.config", {"ANTIVIRUS_ENABLED": False}):
        page = client_request.post(
            "main.email_branding_upload_logo",
            _data=post_data,
            service_id=service_one["id"],
            _expected_status=400,
        )

    assert expected_error in page.text
    assert mock_save_temporary.call_args_list == []


@pytest.mark.parametrize(
    "min_logo_height, expect_error",
    (
        (3, False),
        (5, False),
        (10, True),
    ),
)
def test_POST_email_branding_upload_logo_enforces_minimum_logo_height(
    mocker, client_request, service_one, min_logo_height, expect_error
):
    mocker.patch("app.main.views.service_settings.email_branding.logo_client.save_temporary_logo")
    mocker.patch("app.utils.image_processing.ImageProcessor")

    with mock.patch.dict(
        "app.main.validators.current_app.config",
        {
            "ANTIVIRUS_ENABLED": False,
            "EMAIL_BRANDING_MIN_LOGO_HEIGHT_PX": min_logo_height,
            "EMAIL_BRANDING_MAX_LOGO_WIDTH_PX": 1,
        },
    ):
        page = client_request.post(
            "main.email_branding_upload_logo",
            _data={"logo": (open("tests/test_img_files/its-a-tall-one.png", "rb"), "logo.png")},
            service_id=service_one["id"],
            _expected_status=400 if expect_error else 302,
        )

    if expect_error:
        assert f"Logo must be at least {min_logo_height} pixels high" in page.text


def test_POST_email_branding_upload_logo_resizes_and_pads_wide_short_logo(mocker, client_request, service_one):
    mocker.patch("app.main.views.service_settings.email_branding.logo_client.save_temporary_logo")
    mock_image_processor = mocker.patch("app.main.forms.ImageProcessor")
    mock_image_processor().height = ComparablePropertyMock(side_effect=[26, 13])
    mock_image_processor().width = 100

    with mock.patch.dict(
        "app.main.validators.current_app.config",
        {
            "ANTIVIRUS_ENABLED": False,
            "EMAIL_BRANDING_MIN_LOGO_HEIGHT_PX": 25,
            "EMAIL_BRANDING_MAX_LOGO_WIDTH_PX": 50,
        },
    ):
        client_request.post(
            "main.email_branding_upload_logo",
            _data={"logo": (open("tests/test_img_files/small-but-perfectly-formed.png", "rb"), "logo.png")},
            service_id=service_one["id"],
            _expected_status=302,
        )

    assert mock_image_processor().resize.call_args_list == [mocker.call(new_width=50)]
    assert mock_image_processor().pad.call_args_list == [mocker.call(to_height=25)]


def test_GET_email_branding_set_alt_text_shows_form(client_request, service_one):
    page = client_request.get(
        "main.email_branding_set_alt_text",
        service_id=service_one["id"],
        brand_type="org_banner",
        logo="example.png",
        colour="#abcdef",
    )

    email_preview = page.select_one("iframe")
    email_preview_url = email_preview.get("src")
    email_preview_query_args = parse_qs(urlparse(email_preview_url).query)

    assert email_preview_query_args == {
        "branding_style": ["custom"],
        "brand_type": ["org_banner"],
        "logo": ["example.png"],
        "colour": ["#abcdef"],
    }

    assert normalize_spaces(page.select_one("h1").text) == "Preview your email branding"
    assert normalize_spaces(page.select_one("label[for=alt_text]").text) == "Enter alt text for your logo"
    assert normalize_spaces(page.select_one("main form button").text) == "Save"
    assert normalize_spaces(page.select_one("div#alt_text-hint").text) == "For example, Department for Education"


def test_GET_email_branding_set_alt_text_shows_current_org_in_hint_text(
    client_request,
    service_one,
    mock_get_organisation,
):
    service_one["organisation"] = "1234"

    page = client_request.get(
        "main.email_branding_set_alt_text",
        service_id=service_one["id"],
        brand_type="org_banner",
        logo="example.png",
        colour="#abcdef",
    )
    assert normalize_spaces(page.select_one("div#alt_text-hint").text) == "For example, Test organisation"


@pytest.mark.parametrize(
    "request_params, expected_location",
    (
        (
            {"brand_type": "org"},
            "/services/596364a0-858e-42c8-9062-a8fe822260eb/service-settings/email-branding/upload-logo?brand_type=org",
        ),
        ({}, "/services/596364a0-858e-42c8-9062-a8fe822260eb/service-settings/email-branding/add-banner"),
    ),
)
def test_GET_email_branding_set_alt_text_redirects_on_missing_query_params(
    client_request, service_one, request_params, expected_location
):
    client_request.get(
        "main.email_branding_set_alt_text",
        service_id=service_one["id"],
        **request_params,
        _expected_status=302,
        _expected_redirect=expected_location,
    )


@pytest.mark.parametrize(
    "alt_text, expected_error",
    [
        ("", "Error: Cannot be empty"),
        ("My First Logo", "Error: Do not include the word ‘logo’ in your alt text"),
    ],
)
def test_POST_email_branding_set_alt_text_shows_error(client_request, service_one, alt_text, expected_error):
    page = client_request.post(
        "main.email_branding_set_alt_text",
        service_id=service_one["id"],
        brand_type="org_banner",
        logo="example.png",
        _data={"alt_text": alt_text},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one("#alt_text-error").text) == expected_error


@pytest.mark.parametrize(
    "brand_type, expected_name",
    (
        ("org", "some alt text"),
        ("both", "GOV.UK and some alt text"),
    ),
)
def test_POST_email_branding_set_alt_text_creates_branding_adds_to_pool_and_redirects(
    client_request,
    service_one,
    mock_create_email_branding,
    mock_get_email_branding_name_for_alt_text,
    active_user_with_permissions,
    mock_update_service,
    fake_uuid,
    mocker,
    brand_type,
    expected_name,
):
    mock_flash = mocker.patch("app.main.views.service_settings.email_branding.flash")
    mock_save_permanent = mocker.patch(
        "app.main.views.service_settings.email_branding.logo_client.save_permanent_logo",
        return_value="permanent-example.png",
    )
    mock_should_set_default_org_email_branding = mocker.patch(
        "app.main.views.service_settings.email_branding._should_set_default_org_email_branding", return_value=False
    )
    mock_add_to_branding_pool = mocker.patch(
        "app.organisations_client.add_brandings_to_email_branding_pool", return_value=None
    )
    client_request.post(
        "main.email_branding_set_alt_text",
        service_id=service_one["id"],
        brand_type=brand_type,
        logo="example.png",
        _data={"alt_text": "some alt text"},
        _expected_status=302,
        _expected_redirect=url_for("main.service_settings", service_id=SERVICE_ONE_ID),
    )
    mock_create_email_branding.assert_called_once_with(
        logo="permanent-example.png",
        name=expected_name,
        alt_text="some alt text",
        text=None,
        colour=None,
        brand_type=brand_type,
        created_by_id=active_user_with_permissions["id"],
    )
    mock_add_to_branding_pool.assert_called_once_with(service_one["organisation"], [fake_uuid])
    mock_update_service.assert_called_once_with(
        service_one["id"],
        email_branding=fake_uuid,
    )
    mock_flash.assert_called_once_with(
        "You’ve changed your email branding. Send yourself an email to make sure it looks OK.",
        "default_with_tick",
    )
    mock_should_set_default_org_email_branding.assert_called_once_with(None)
    assert mock_save_permanent.call_args_list == [
        mocker.call(
            "example.png",
            logo_type="email",
            logo_key_extra="some alt text",
        )
    ]


def test_POST_email_branding_set_alt_text_creates_branding_sets_org_default_if_appropriate(
    client_request,
    service_one,
    mock_create_email_branding,
    mock_get_email_branding_name_for_alt_text,
    active_user_with_permissions,
    mock_update_service,
    mock_get_organisation,
    mock_get_organisation_services,
    mock_update_organisation,
    fake_uuid,
    mocker,
):
    service_one["organisation"] = ORGANISATION_ID
    mock_save_permanent = mocker.patch(
        "app.main.views.service_settings.email_branding.logo_client.save_permanent_logo",
        return_value="permanent-example.png",
    )
    mock_should_set_default_org_email_branding = mocker.patch(
        "app.main.views.service_settings.email_branding._should_set_default_org_email_branding", return_value=True
    )
    mock_add_to_branding_pool = mocker.patch(
        "app.organisations_client.add_brandings_to_email_branding_pool", return_value=None
    )
    client_request.post(
        "main.email_branding_set_alt_text",
        service_id=service_one["id"],
        brand_type="org",
        logo="example.png",
        branding_choice="organisation",
        _data={"alt_text": "some alt text"},
        _expected_status=302,
        _expected_redirect=url_for("main.service_settings", service_id=SERVICE_ONE_ID),
    )
    mock_create_email_branding.assert_called_once_with(
        logo="permanent-example.png",
        name="some alt text",
        alt_text="some alt text",
        text=None,
        colour=None,
        brand_type="org",
        created_by_id=active_user_with_permissions["id"],
    )
    mock_add_to_branding_pool.assert_called_once_with(service_one["organisation"], [fake_uuid])
    mock_should_set_default_org_email_branding.assert_called_once_with("organisation")
    mock_update_organisation.assert_called_once_with(
        ORGANISATION_ID, cached_service_ids=ANY, email_branding_id=fake_uuid
    )
    assert mock_save_permanent.call_args_list == [
        mocker.call(
            "example.png",
            logo_type="email",
            logo_key_extra="some alt text",
        )
    ]


@pytest.mark.parametrize(
    "org_type, url_params, back_button_url",
    [
        ("central", {}, ".email_branding_choose_logo"),
        ("local", {}, ".email_branding_options"),
        ("local", {"back_link": ".email_branding_options"}, ".email_branding_options"),
    ],
)
def test_email_branding_choose_banner_type_page(
    client_request,
    mocker,
    service_one,
    organisation_one,
    mock_get_empty_email_branding_pool,
    org_type,
    url_params,
    back_button_url,
):
    organisation_one["organisation_type"] = org_type
    service_one["organisation"] = organisation_one
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    page = client_request.get("main.email_branding_choose_banner_type", service_id=SERVICE_ONE_ID, **url_params)

    form = page.select_one("form")
    submit_button = page.select_one("button.page-footer__button")
    back_button = page.select_one("a.govuk-back-link")

    assert page.select_one("h1").text.strip() == "Does your logo appear on a coloured background?"

    assert form["method"] == "post"
    assert "Continue" in submit_button.text
    assert [radio["value"] for radio in page.select("input[type=radio]")] == ["org_banner", "org"]

    assert back_button["href"] == url_for(back_button_url, service_id=SERVICE_ONE_ID)


@pytest.mark.parametrize(
    "organisation_type",
    (
        # Anything not Central Government or NHS
        "emergency_service",
        "local",
        "other",
        "school_or_college",
    ),
)
@pytest.mark.parametrize(
    "pool_contents",
    (
        ".email_branding_options",
        create_email_branding_pool(),
    ),
)
def test_email_branding_choose_banner_type_page_when_no_organisation(
    client_request,
    mocker,
    service_one,
    organisation_type,
    pool_contents,
):
    service_one["organisation_type"] = organisation_type
    service_one["organisation"] = None

    page = client_request.get("main.email_branding_choose_banner_type", service_id=SERVICE_ONE_ID)

    back_button = page.select_one("a.govuk-back-link")
    assert back_button["href"] == url_for(".email_branding_options", service_id=SERVICE_ONE_ID)


@pytest.mark.parametrize(
    "organisation_type, expected_status",
    (
        ("central", 200),
        ("local", 200),
    ),
)
def test_any_org_type_can_see_email_branding_choose_banner_type_page(
    client_request, service_one, organisation_type, expected_status
):
    service_one["organisation_type"] = organisation_type

    client_request.get(
        ".email_branding_choose_banner_type",
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_status,
    )


@pytest.mark.parametrize(
    "selected_option, expected_endpoint, url_for_kwargs",
    [
        ("org", ".email_branding_upload_logo", {"brand_type": "org"}),
        ("org_banner", ".email_branding_choose_banner_colour", {"brand_type": "org_banner"}),
    ],
)
def test_email_branding_choose_banner_type_redirects_to_right_page(
    client_request, service_one, selected_option, expected_endpoint, url_for_kwargs
):
    client_request.post(
        ".email_branding_choose_banner_type",
        service_id=SERVICE_ONE_ID,
        _data={"banner": selected_option},
        _expected_status=302,
        _expected_redirect=url_for(expected_endpoint, service_id=SERVICE_ONE_ID, **url_for_kwargs),
    )


def test_email_branding_choose_banner_type_shows_error_summary_on_invalid_data(client_request, service_one):
    page = client_request.post(
        ".email_branding_choose_banner_type",
        service_id=SERVICE_ONE_ID,
        _data={"banner": "invalid"},
        _expected_status=400,
    )

    error_summary = page.select_one(".govuk-error-summary")
    assert normalize_spaces(error_summary.text) == "There is a problem Select an option"
    assert error_summary.select_one("a").get("href") == "#banner"

    assert "Error: Select an option" in page.select_one("#banner").text


def test_GET_email_branding_choose_banner_colour(client_request, service_one):
    page = client_request.get(
        "main.email_branding_choose_banner_colour",
        brand_type="org_banner",
        service_id=service_one["id"],
    )

    back_button = page.select_one("a.govuk-back-link")
    form = page.select_one("form")
    submit_button = form.select_one("button")
    text_input = form.select_one("input")
    skip_link = page.select("main a")[-1]

    assert back_button["href"] == url_for(
        "main.email_branding_choose_banner_type", service_id=service_one["id"], brand_type="org_banner"
    )
    assert form["method"] == "post"
    assert "Continue" in submit_button.text
    assert text_input["name"] == "hex_colour"

    assert skip_link is not None
    assert skip_link["href"] == url_for(
        "main.email_branding_request",
        service_id=service_one["id"],
        back_link=".email_branding_choose_banner_colour",
        brand_type="org_banner",
    )
    assert skip_link.text == "I do not know the hex colour code"


def test_POST_email_branding_choose_banner_colour(client_request, service_one):
    client_request.post(
        "main.email_branding_choose_banner_colour",
        service_id=service_one["id"],
        brand_type="org_banner",
        _data={"hex_colour": "#abcdef"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.email_branding_upload_logo", service_id=service_one["id"], brand_type="org_banner", colour="#abcdef"
        ),
    )


@pytest.mark.parametrize(
    "hex_colour, expected_query_param",
    (
        ("#abc", "#abc"),
        ("#abcdef", "#abcdef"),
        ("abc", "#abc"),
        ("abcdef", "#abcdef"),
    ),
)
def test_POST_email_branding_choose_banner_colour_handles_hex_colour_variations(
    client_request, service_one, hex_colour, expected_query_param
):
    client_request.post(
        "main.email_branding_choose_banner_colour",
        service_id=service_one["id"],
        _data={"hex_colour": hex_colour},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.email_branding_upload_logo", service_id=service_one["id"], colour=expected_query_param
        ),
    )


def test_POST_email_branding_choose_banner_colour_invalid_hex_code(client_request, service_one):
    page = client_request.post(
        "main.email_branding_choose_banner_colour",
        service_id=service_one["id"],
        _data={"hex_colour": "BAD-CODE"},
        _expected_status=400,
    )

    assert "Must be a valid hex colour code" in page.text

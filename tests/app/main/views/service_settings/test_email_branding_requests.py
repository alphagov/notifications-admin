from unittest.mock import ANY, PropertyMock

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
    normalize_spaces,
)


def test_email_branding_request_page_when_no_branding_is_set(
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
        ".email_branding_request",
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
def test_email_branding_request_page_shows_branding_pool_options_if_branding_pool_set_for_org(
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

    page = client_request.get(".email_branding_request", service_id=SERVICE_ONE_ID)

    assert [
        (radio["value"], page.select_one("label[for={}]".format(radio["id"])).text.strip())
        for radio in page.select("input[type=radio]")
    ] == expected_options


def test_email_branding_request_does_not_show_nhs_branding_twice(
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

    page = client_request.get(".email_branding_request", service_id=SERVICE_ONE_ID)

    assert [
        (radio["value"], page.select_one(f'label[for={radio["id"]}]').text.strip())
        for radio in page.select("input[type=radio]")
    ] == [
        (EmailBranding.NHS_ID, "NHS"),
        ("email-branding-1-id", "Email branding name 1"),
        ("email-branding-2-id", "Email branding name 2"),
        ("something_else", "Something else"),
    ]


def test_email_branding_request_page_redirects_to_something_else_page_if_that_is_only_option(
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

    client_request.get(
        ".email_branding_request",
        service_id=SERVICE_ONE_ID,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.email_branding_something_else", service_id=SERVICE_ONE_ID, back_link=".service_settings"
        ),
    )


def test_email_branding_request_page_redirects_nhs_specific_page(
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
        ".email_branding_request",
        service_id=SERVICE_ONE_ID,
        _data={"options": EmailBranding.NHS_ID},
        _expected_redirect=url_for(
            "main.email_branding_nhs",
            service_id=SERVICE_ONE_ID,
        ),
    )


def test_email_branding_request_redirects_to_branding_preview_for_a_branding_pool_option(
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
        ".email_branding_request",
        service_id=SERVICE_ONE_ID,
        _data={"options": "email-branding-1-id"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.email_branding_pool_option",
            service_id=SERVICE_ONE_ID,
            branding_option="email-branding-1-id",
        ),
    )


def test_email_branding_pool_option_page_displays_preview_of_chosen_branding(
    service_one, organisation_one, client_request, mocker, mock_get_email_branding_pool
):
    organisation_one["organisation_type"] = "central"
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    page = client_request.get(
        ".email_branding_pool_option", service_id=SERVICE_ONE_ID, branding_option="email-branding-1-id"
    )

    assert page.select_one("iframe")["src"] == url_for("main.email_template", branding_style="email-branding-1-id")


def test_email_branding_pool_option_page_redirects_to_branding_request_page_if_branding_option_not_found(
    service_one, organisation_one, client_request, mocker, mock_get_email_branding_pool
):
    organisation_one["organisation_type"] = "central"
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    client_request.get(
        ".email_branding_pool_option",
        service_id=SERVICE_ONE_ID,
        branding_option="some-unknown-branding-id",
        _expected_status=302,
        _expected_redirect=url_for("main.email_branding_request", service_id=SERVICE_ONE_ID),
    )


def test_email_branding_pool_option_changes_email_branding_when_user_confirms(
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
        ".email_branding_pool_option",
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


def test_email_branding_request_page_shows_branding_if_set(
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

    page = client_request.get(".email_branding_request", service_id=SERVICE_ONE_ID)
    assert page.select_one("iframe")["src"] == url_for("main.email_template", branding_style="some-random-branding")


def test_email_branding_request_page_back_link(
    client_request, mock_get_email_branding_pool, service_one, organisation_one, mocker
):
    organisation_one["organisation_type"] = "central"
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    page = client_request.get(".email_branding_request", service_id=SERVICE_ONE_ID)

    back_link = page.select("a[class=govuk-back-link]")
    assert back_link[0].attrs["href"] == url_for(".service_settings", service_id=SERVICE_ONE_ID)


@pytest.mark.parametrize(
    "data, org_type, endpoint, extra_args",
    (
        (
            {
                "options": "govuk",
            },
            "central",
            "main.email_branding_govuk",
            {},
        ),
        (
            {
                "options": "govuk_and_org",
            },
            "central",
            "main.email_branding_choose_logo",
            {"branding_choice": "govuk_and_org"},
        ),
        (
            {
                "options": "organisation",
            },
            "central",
            "main.email_branding_choose_logo",
            {"branding_choice": "organisation"},
        ),
        (
            {
                "options": "something_else",
            },
            "central",
            "main.email_branding_choose_logo",
            {"branding_choice": "something_else"},
        ),
        (
            {
                "options": "something_else",
            },
            "local",
            "main.email_branding_something_else",
            {"back_link": ".email_branding_request"},
        ),
        (
            {
                "options": EmailBranding.NHS_ID,
            },
            "nhs_local",
            "main.email_branding_nhs",
            {},
        ),
    ),
)
def test_email_branding_request_submit(
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
        ".email_branding_request",
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=302,
        _expected_redirect=url_for(
            endpoint,
            service_id=SERVICE_ONE_ID,
            **extra_args,
        ),
    )


def test_email_branding_request_submit_when_no_radio_button_is_selected(
    client_request,
    service_one,
    mock_get_empty_email_branding_pool,
    mock_get_email_branding,
):
    service_one["email_branding"] = sample_uuid()

    page = client_request.post(
        ".email_branding_request",
        service_id=SERVICE_ONE_ID,
        _data={"options": ""},
        _follow_redirects=True,
    )
    assert page.select_one("h1").text == "Change email branding"
    assert normalize_spaces(page.select_one(".error-message").text) == "Select an option"


@pytest.mark.parametrize(
    "endpoint, expected_heading",
    [
        ("main.email_branding_govuk_and_org", "Before you request new branding"),
        ("main.email_branding_organisation", "When you request new branding"),
    ],
)
def test_email_branding_description_pages_for_org_branding(
    client_request,
    mocker,
    service_one,
    organisation_one,
    mock_get_empty_email_branding_pool,
    mock_get_email_branding,
    endpoint,
    expected_heading,
):
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
    assert page.select_one("h1").text == expected_heading
    assert normalize_spaces(page.select_one(".page-footer button").text) == "Request new branding"


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


def test_email_branding_something_else_page(client_request, service_one, mock_get_empty_email_branding_pool):
    # expect to have a "NHS" option as well as the
    # fallback, so back button goes to choices page
    service_one["organisation_type"] = "nhs_central"

    page = client_request.get(
        "main.email_branding_something_else",
        service_id=SERVICE_ONE_ID,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Describe the branding you want"
    assert page.select_one("textarea")["name"] == ("something_else")
    assert normalize_spaces(page.select_one(".page-footer button").text) == "Request new branding"
    assert page.select_one(".govuk-back-link")["href"] == url_for(
        "main.email_branding_request",
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
def test_email_branding_something_else_back_to_new_email_branding_query_params(
    client_request, service_one, mock_get_empty_email_branding_pool, back_view, back_view_args
):
    service_one["organisation_type"] = "nhs_central"

    page = client_request.get(
        "main.email_branding_something_else",
        service_id=SERVICE_ONE_ID,
        back_link=back_view,
        **back_view_args,
    )
    back_link = page.select_one(".govuk-back-link")
    assert back_link["href"] == url_for(back_view, service_id=SERVICE_ONE_ID, **back_view_args)


@pytest.mark.parametrize("back_link", [".service_settings", ".email_branding_request", ".email_branding_choose_logo"])
def test_email_branding_something_else_page_back_link_from_args(
    client_request, service_one, mock_get_empty_email_branding_pool, back_link
):
    # expect to have a "NHS" option as well as the
    # fallback, so "something else" is not an only option
    service_one["organisation_type"] = "nhs_central"

    page = client_request.get("main.email_branding_something_else", service_id=SERVICE_ONE_ID, back_link=back_link)
    assert normalize_spaces(page.select_one("h1").text) == "Describe the branding you want"
    assert page.select_one(".govuk-back-link")["href"] == url_for(
        back_link,
        service_id=SERVICE_ONE_ID,
    )


def test_get_email_branding_something_else_page_is_only_option(
    client_request, service_one, mock_get_empty_email_branding_pool
):
    # should only have a "something else" option
    # so back button goes back to settings page
    service_one["organisation_type"] = "other"

    page = client_request.get(
        "main.email_branding_something_else",
        service_id=SERVICE_ONE_ID,
    )
    assert page.select_one(".govuk-back-link")["href"] == url_for(
        "main.service_settings",
        service_id=SERVICE_ONE_ID,
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        ("main.email_branding_govuk"),
        ("main.email_branding_govuk_and_org"),
        ("main.email_branding_nhs"),
        ("main.email_branding_organisation"),
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


def test_email_branding_govuk_and_org_submit(
    mocker,
    client_request,
    service_one,
    organisation_one,
    no_reply_to_email_addresses,
    mock_get_empty_email_branding_pool,
    mock_get_email_branding,
    single_sms_sender,
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

    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mock_send_ticket_to_zendesk = mocker.patch(
        "app.main.views.service_settings.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )

    page = client_request.post(
        ".email_branding_govuk_and_org",
        service_id=SERVICE_ONE_ID,
        _follow_redirects=True,
    )

    mock_create_ticket.assert_called_once_with(
        ANY,
        message="\n".join(
            [
                "Organisation: organisation one",
                "Service: service one",
                "http://localhost/services/596364a0-858e-42c8-9062-a8fe822260eb",
                "",
                "---",
                "Current branding: Organisation name",
                "Branding requested: GOV.UK and organisation one\n",
            ]
        ),
        subject="Email branding request - service one",
        ticket_type="question",
        user_name="Test User",
        user_email="test@user.gov.uk",
        org_id=ORGANISATION_ID,
        org_type="central",
        service_id=SERVICE_ONE_ID,
    )
    mock_send_ticket_to_zendesk.assert_called_once()
    assert normalize_spaces(page.select_one(".banner-default").text) == (
        "Thanks for your branding request. We’ll get back to you " "within one working day."
    )


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


def test_email_branding_organisation_submit(
    mocker,
    client_request,
    service_one,
    organisation_one,
    no_reply_to_email_addresses,
    mock_get_empty_email_branding_pool,
    mock_get_email_branding,
    single_sms_sender,
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

    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mock_send_ticket_to_zendesk = mocker.patch(
        "app.main.views.service_settings.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )

    page = client_request.post(
        ".email_branding_organisation",
        service_id=SERVICE_ONE_ID,
        _follow_redirects=True,
    )

    mock_create_ticket.assert_called_once_with(
        ANY,
        message="\n".join(
            [
                "Organisation: organisation one",
                "Service: service one",
                "http://localhost/services/596364a0-858e-42c8-9062-a8fe822260eb",
                "",
                "---",
                "Current branding: Organisation name",
                "Branding requested: organisation one\n",
            ]
        ),
        subject="Email branding request - service one",
        ticket_type="question",
        user_name="Test User",
        user_email="test@user.gov.uk",
        org_id=ORGANISATION_ID,
        org_type="central",
        service_id=SERVICE_ONE_ID,
    )
    mock_send_ticket_to_zendesk.assert_called_once()
    assert normalize_spaces(page.select_one(".banner-default").text) == (
        "Thanks for your branding request. We’ll get back to you " "within one working day."
    )


def test_email_branding_something_else_submit(
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
        "app.main.views.service_settings.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )

    page = client_request.post(
        ".email_branding_something_else",
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
                "Branding requested: Something else\n",
                "Homer Simpson\n",
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
        "Thanks for your branding request. We’ll get back to you " "within one working day."
    )


def test_email_branding_something_else_submit_shows_error_if_textbox_is_empty(
    client_request, mock_get_empty_email_branding_pool
):
    page = client_request.post(
        ".email_branding_something_else",
        service_id=SERVICE_ONE_ID,
        _data={"something_else": ""},
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Describe the branding you want"
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == "Error: Cannot be empty"


def test_email_branding_choose_logo_page(client_request, service_one):
    page = client_request.get(
        "main.email_branding_choose_logo",
        service_id=SERVICE_ONE_ID,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Choose a logo for your emails"

    assert page.select_one(".govuk-back-link")["href"] == url_for(
        "main.email_branding_request",
        service_id=SERVICE_ONE_ID,
    )

    assert [
        (radio["value"], page.select_one(f"label.govuk-label[for=branding_options-{i}]").text.strip())
        for i, radio in enumerate(page.select("input[type=radio]"))
    ] == [
        ("single_identity", "Create a government identity logo"),
        ("org", "Use your own logo"),
    ]


def test_only_central_org_services_can_see_email_branding_choose_logo_page(client_request, service_one):
    service_one["organisation_type"] = "local"

    client_request.get(
        "main.email_branding_choose_logo",
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
    )


@pytest.mark.parametrize(
    "selected_option, expected_endpoint, extra_url_args",
    [
        ("org", ".email_branding_something_else", {"back_link": ".email_branding_choose_logo"}),
        ("single_identity", ".email_branding_request_government_identity_logo", {}),
    ],
)
def test_email_branding_choose_logo_redirects_to_right_page(
    client_request, service_one, selected_option, expected_endpoint, extra_url_args
):
    client_request.post(
        ".email_branding_choose_logo",
        service_id=SERVICE_ONE_ID,
        _data={"branding_options": selected_option},
        _expected_status=302,
        _expected_redirect=url_for(expected_endpoint, service_id=SERVICE_ONE_ID, **extra_url_args),
    )

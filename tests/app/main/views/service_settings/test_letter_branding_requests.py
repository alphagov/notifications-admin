from unittest.mock import ANY, PropertyMock

import pytest
from flask import url_for
from notifications_utils.clients.zendesk.zendesk_client import NotifySupportTicket

from app.models.branding import LetterBranding
from tests import organisation_json, sample_uuid
from tests.conftest import (
    ORGANISATION_ID,
    SERVICE_ONE_ID,
    TEMPLATE_ONE_ID,
    normalize_spaces,
)


@pytest.mark.parametrize(
    "organisation_type, is_org_set, letter_branding_pool, expected_options",
    (
        (
            "nhs_central",
            True,
            [
                {"id": "1234", "name": "Brand 1", "filename": "brand_1"},
                {"id": "5678", "name": "Brand 2", "filename": "brand_2"},
            ],
            [
                (LetterBranding.NHS_ID, "NHS"),
                ("1234", "Brand 1"),
                ("5678", "Brand 2"),
                ("something_else", "Something else"),
            ],
        ),
        (
            "nhs_central",
            False,
            [],
            [
                (LetterBranding.NHS_ID, "NHS"),
                ("something_else", "Something else"),
            ],
        ),
        ("other", False, [], None),
    ),
)
def test_letter_branding_request_page_when_no_branding_is_set(
    service_one,
    client_request,
    mock_get_email_branding,
    mock_get_letter_branding_by_id,
    mocker,
    organisation_type,
    is_org_set,
    letter_branding_pool,
    expected_options,
):
    service_one["letter_branding"] = None
    service_one["organisation_type"] = organisation_type

    if is_org_set:
        mocker.patch(
            "app.models.service.Service.organisation_id",
            new_callable=PropertyMock,
            return_value=ORGANISATION_ID,
        )
        mocker.patch(
            "app.organisations_client.get_organisation",
            return_value=organisation_json(id_=ORGANISATION_ID, name="NHS Org 1", organisation_type=organisation_type),
        )
        mocker.patch("app.models.branding.LetterBrandingPool.client_method", side_effect=[letter_branding_pool])

    page = client_request.get(".letter_branding_request", service_id=SERVICE_ONE_ID)

    assert mock_get_email_branding.called is False
    assert mock_get_letter_branding_by_id.called is False

    assert normalize_spaces(page.select_one("main p").text) == "Your letters currently have no branding."

    button_text = normalize_spaces(page.select_one(".page-footer button").text)
    assert button_text == "Continue"

    if expected_options:
        assert [
            (radio["value"], page.select_one("label[for={}]".format(radio["id"])).text.strip())
            for radio in page.select("input[type=radio]")
        ] == expected_options
        assert page.select_one(".conditional-radios-panel#panel-something-else textarea")["name"] == "something_else"
    else:
        assert page.select_one("textarea")["name"] == "something_else"
        assert not page.select(".conditional-radios-panel")


def test_letter_branding_request_page_when_branding_is_set_already(
    client_request,
    service_one,
    fake_uuid,
    mock_get_letter_branding_by_id,
):
    service_one["letter_branding"] = fake_uuid
    page = client_request.get(".letter_branding_request", service_id=SERVICE_ONE_ID)
    assert normalize_spaces(page.select_one("main p").text) == "Your letters currently have HM Government branding."


@pytest.mark.parametrize(
    "from_template,back_link_url",
    [
        (
            None,
            "/services/{}/service-settings".format(SERVICE_ONE_ID),
        ),
        (
            TEMPLATE_ONE_ID,
            "/services/{}/templates/{}".format(SERVICE_ONE_ID, TEMPLATE_ONE_ID),
        ),
    ],
)
def test_letter_branding_request_page_back_link(
    client_request,
    from_template,
    back_link_url,
):
    if from_template:
        page = client_request.get(".letter_branding_request", service_id=SERVICE_ONE_ID, from_template=from_template)
    else:
        page = client_request.get(".letter_branding_request", service_id=SERVICE_ONE_ID)

    back_link = page.select("a[class=govuk-back-link]")
    assert back_link[0].attrs["href"] == back_link_url


def test_letter_branding_request_redirects_to_branding_preview_for_a_branding_pool_option(
    client_request,
    service_one,
    mocker,
    mock_get_letter_branding_pool,
):
    mocker.patch(
        "app.models.service.Service.organisation_id",
        new_callable=PropertyMock,
        return_value=ORGANISATION_ID,
    )
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, name="Org 1"),
    )

    client_request.post(
        ".letter_branding_request",
        service_id=SERVICE_ONE_ID,
        _data={"options": "1234"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.letter_branding_pool_option",
            service_id=SERVICE_ONE_ID,
            branding_option="1234",
        ),
    )


@pytest.mark.parametrize(
    "org_name, expected_organisation",
    (
        (None, "Can’t tell (domain is user.gov.uk)"),
        ("Test Organisation", "Test Organisation"),
    ),
)
def test_letter_branding_request_submit_choose_something_else(
    client_request,
    service_one,
    mocker,
    mock_get_letter_branding_by_id,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    mock_get_empty_letter_branding_pool,
    org_name,
    expected_organisation,
):
    service_one["letter_branding"] = sample_uuid()
    organisation_id = ORGANISATION_ID if org_name else None

    mocker.patch(
        "app.models.service.Service.organisation_id",
        new_callable=PropertyMock,
        return_value=organisation_id,
    )
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(name=org_name),
    )

    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mock_send_ticket_to_zendesk = mocker.patch(
        "app.main.views.service_settings.index.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )

    page = client_request.post(
        ".letter_branding_request",
        service_id=SERVICE_ONE_ID,
        _data={
            "options": "something_else",
            "something_else": "Homer Simpson",
        },
        _follow_redirects=True,
    )

    mock_create_ticket.assert_called_once_with(
        ANY,
        message="\n".join(
            [
                "Organisation: {}",
                "Service: service one",
                "http://localhost/services/596364a0-858e-42c8-9062-a8fe822260eb",
                "",
                "---",
                "Current branding: HM Government",
                "Branding requested: Something else\n\nHomer Simpson\n",
            ]
        ).format(expected_organisation),
        subject="Letter branding request - service one",
        ticket_type="question",
        user_name="Test User",
        user_email="test@user.gov.uk",
        org_id=organisation_id,
        org_type="central",
        service_id=SERVICE_ONE_ID,
    )
    mock_send_ticket_to_zendesk.assert_called_once()
    assert normalize_spaces(page.select_one(".banner-default").text) == (
        "Thanks for your branding request. We’ll get back to you within one working day."
    )


@pytest.mark.parametrize(
    "data, error_message",
    (
        ({"options": "something_else"}, "Cannot be empty"),  # no data in 'something_else' textbox
        ({"options": ""}, "Select an option"),  # no radio button selected
    ),
)
def test_letter_branding_request_submit_when_form_has_missing_data(
    client_request,
    mocker,
    service_one,
    organisation_one,
    mock_get_letter_branding_by_id,
    mock_get_empty_letter_branding_pool,
    data,
    error_message,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )
    service_one["letter_branding"] = sample_uuid()
    service_one["organisation"] = organisation_one

    page = client_request.post(
        ".letter_branding_request",
        service_id=SERVICE_ONE_ID,
        _data=data,
        _follow_redirects=True,
    )
    assert page.select_one("h1").text == "Change letter branding"
    assert normalize_spaces(page.select_one(".error-message").text) == error_message


@pytest.mark.parametrize("from_template", [None, TEMPLATE_ONE_ID])
def test_letter_branding_request_submit_redirects_if_from_template_is_set(
    client_request,
    service_one,
    mocker,
    mock_get_empty_letter_branding_pool,
    from_template,
):
    mocker.patch("app.main.views.service_settings.index.zendesk_client.send_ticket_to_zendesk", autospec=True)
    data = {"options": "something_else", "something_else": "Homer Simpson"}

    if from_template:
        client_request.post(
            ".letter_branding_request",
            service_id=SERVICE_ONE_ID,
            from_template=from_template,
            _data=data,
            _expected_redirect=url_for(
                "main.view_template",
                service_id=SERVICE_ONE_ID,
                template_id=from_template,
            ),
        )
    else:
        client_request.post(
            ".letter_branding_request",
            service_id=SERVICE_ONE_ID,
            _data=data,
            _expected_redirect=url_for("main.service_settings", service_id=SERVICE_ONE_ID),
        )


def test_letter_branding_submit_when_something_else_is_only_option(
    client_request,
    service_one,
    mocker,
    mock_get_letter_branding_by_id,
):
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mocker.patch(
        "app.main.views.service_settings.index.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )

    client_request.post(
        ".letter_branding_request",
        service_id=SERVICE_ONE_ID,
        _data={
            "something_else": "Homer Simpson",
        },
    )

    assert (
        "Current branding: no\nBranding requested: Something else\n" "\nHomer Simpson"
    ) in mock_create_ticket.call_args_list[0][1]["message"]


def test_letter_branding_request_redirects_to_upload_logo_for_platform_admins(
    client_request, platform_admin_user, service_one, mocker
):
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    client_request.login(platform_admin_user)

    client_request.post(
        ".letter_branding_request",
        service_id=SERVICE_ONE_ID,
        _data={
            "options": "something_else",
            "something_else": "this text is unused but required to pass form validation",
        },
        _expected_redirect=url_for(
            "main.letter_branding_upload_branding", service_id=SERVICE_ONE_ID, branding_choice="something_else"
        ),
    )
    mock_create_ticket.assert_not_called()


def test_letter_branding_pool_option_page_displays_preview_of_chosen_branding(
    service_one, organisation_one, client_request, mocker, mock_get_letter_branding_pool
):
    organisation_one["organisation_type"] = "central"
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    page = client_request.get(".letter_branding_pool_option", service_id=SERVICE_ONE_ID, branding_option="1234")

    assert page.select_one("iframe")["src"] == url_for("main.letter_template", branding_style="1234")


def test_letter_branding_pool_option_page_redirects_to_branding_request_page_if_branding_option_not_found(
    service_one, organisation_one, client_request, mocker, mock_get_letter_branding_pool
):
    organisation_one["organisation_type"] = "central"
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    client_request.get(
        ".letter_branding_pool_option",
        service_id=SERVICE_ONE_ID,
        branding_option="some-unknown-branding-id",
        _expected_status=302,
        _expected_redirect=url_for("main.letter_branding_request", service_id=SERVICE_ONE_ID),
    )


def test_letter_branding_pool_option_changes_letter_branding_when_user_confirms(
    mocker,
    service_one,
    organisation_one,
    client_request,
    no_reply_to_email_addresses,
    single_sms_sender,
    mock_get_letter_branding_pool,
    mock_update_service,
):
    organisation_one["organisation_type"] = "central"
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    page = client_request.post(
        ".letter_branding_pool_option",
        service_id=SERVICE_ONE_ID,
        branding_option="1234",
        _follow_redirects=True,
    )

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        letter_branding="1234",
    )
    assert page.select_one("h1").text == "Settings"
    assert normalize_spaces(page.select_one(".banner-default").text) == "You’ve updated your letter branding"

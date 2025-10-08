from io import BytesIO
from unittest.mock import ANY, PropertyMock

import pytest
from flask import g, url_for
from notifications_utils.clients.zendesk.zendesk_client import NotifySupportTicket

from app.main.views_nl.service_settings.branding import (
    _should_set_default_org_letter_branding,
)
from app.models.branding import LetterBranding
from app.models.service import Service
from tests import organisation_json, sample_uuid, service_json
from tests.conftest import (
    ORGANISATION_ID,
    SERVICE_ONE_ID,
    TEMPLATE_ONE_ID,
    normalize_spaces,
)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
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
        ("other", False, [], []),
    ),
)
def test_letter_branding_options_page_when_no_branding_is_set(
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
        mocker.patch("app.models.branding.LetterBrandingPool._get_items", side_effect=[letter_branding_pool])

    page = client_request.get(".letter_branding_options", service_id=SERVICE_ONE_ID)

    assert mock_get_email_branding.called is False
    assert mock_get_letter_branding_by_id.called is False

    assert normalize_spaces(page.select_one("main p").text) == "Your letters currently have no branding."

    # no preview if no existing branding
    assert not page.select_one("iframe")

    button_text = normalize_spaces(page.select_one(".page-footer button").text)
    assert button_text == "Continue"

    assert not page.select(".govuk-radios__item input[checked]")
    assert [
        (radio["value"], page.select_one(f"label[for={radio['id']}]").text.strip())
        for radio in page.select("input[type=radio]")
    ] == expected_options


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_letter_branding_options_page_when_branding_is_set_already(
    client_request,
    service_one,
    fake_uuid,
    mock_get_letter_branding_by_id,
):
    service_one["letter_branding"] = fake_uuid
    page = client_request.get(".letter_branding_options", service_id=SERVICE_ONE_ID)
    assert normalize_spaces(page.select_one("main p").text) == "Your letters currently have HM Government branding."

    assert page.select_one("main img")["src"] == url_for(
        "no_cookie.letter_branding_preview_image",
        branding_style=fake_uuid,
    )
    assert page.select_one("main img")["alt"] == "Preview of current letter branding"


def test_letter_branding_options_shows_query_param_branding_choice_selected(
    client_request, service_one, organisation_one, mocker, mock_get_letter_branding_pool
):
    service_one["organisation"] = organisation_one
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )
    page = client_request.get(".letter_branding_options", service_id=SERVICE_ONE_ID, branding_choice="1234")

    checked_radio_button = page.select(".govuk-radios__item input[checked]")

    assert len(checked_radio_button) == 1
    assert checked_radio_button[0]["value"] == "1234"


@pytest.mark.parametrize(
    "from_template,back_link_url",
    [
        (
            None,
            f"/services/{SERVICE_ONE_ID}/service-settings",
        ),
        (
            TEMPLATE_ONE_ID,
            f"/services/{SERVICE_ONE_ID}/templates/{TEMPLATE_ONE_ID}",
        ),
    ],
)
def test_letter_branding_options_page_back_link(
    client_request,
    from_template,
    back_link_url,
):
    if from_template:
        page = client_request.get(".letter_branding_options", service_id=SERVICE_ONE_ID, from_template=from_template)
    else:
        page = client_request.get(".letter_branding_options", service_id=SERVICE_ONE_ID)

    back_link = page.select("a.govuk-back-link")
    assert back_link[0].attrs["href"] == back_link_url


def test_letter_branding_options_redirects_to_branding_preview_for_a_branding_pool_option(
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
        ".letter_branding_options",
        service_id=SERVICE_ONE_ID,
        _data={"options": "1234"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.branding_option_preview",
            service_id=SERVICE_ONE_ID,
            branding_choice="1234",
            branding_type="letter",
        ),
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_letter_branding_options_errors_when_no_option_selected(
    client_request,
    mocker,
    service_one,
    organisation_one,
    mock_get_letter_branding_by_id,
    mock_get_empty_letter_branding_pool,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )
    service_one["letter_branding"] = sample_uuid()
    service_one["organisation"] = organisation_one

    page = client_request.post(".letter_branding_options", service_id=SERVICE_ONE_ID, _data={}, _expected_status=200)
    assert page.select_one("h1").text == "Change letter branding"
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == "Error: Select an option"


def test_letter_branding_options_does_not_error_when_no_options_available_at_all(
    client_request,
    mocker,
    service_one,
    organisation_one,
    mock_get_letter_branding_by_id,
    mock_get_empty_letter_branding_pool,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )
    # a non-nhs service with no org and no existing branding will only have "something else" available
    # so we won't show them any options
    service_one["letter_branding"] = None
    service_one["organisation"] = None

    client_request.post(
        ".letter_branding_options",
        service_id=SERVICE_ONE_ID,
        _data={"options": "something_else"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.letter_branding_upload_branding",
            service_id=SERVICE_ONE_ID,
            branding_choice="something_else",
        ),
    )


def test_letter_branding_options_redirects_to_upload_logo(client_request, mocker):
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")

    client_request.post(
        ".letter_branding_options",
        service_id=SERVICE_ONE_ID,
        _data={"options": "something_else"},
        _expected_redirect=url_for(
            "main.letter_branding_upload_branding", service_id=SERVICE_ONE_ID, branding_choice="something_else"
        ),
    )
    mock_create_ticket.assert_not_called()


def test_letter_branding_options_redirects_to_nhs_page(
    client_request,
    service_one,
    organisation_one,
    mocker,
):
    service_one["organisation"] = organisation_one["id"]
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)
    mocker.patch(
        "app.models.branding.LetterBrandingPool._get_items",
        return_value=[{"name": "NHS", "id": LetterBranding.NHS_ID}],
    )

    client_request.post(
        ".letter_branding_options",
        service_id=SERVICE_ONE_ID,
        _data={"options": LetterBranding.NHS_ID},
        _expected_redirect=url_for(
            "main.branding_nhs",
            service_id=SERVICE_ONE_ID,
            branding_type="letter",
            branding_choice=LetterBranding.NHS_ID,
        ),
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_GET_letter_branding_request_renders_form(
    client_request,
    mock_get_letter_branding_by_id,
):
    page = client_request.get(".letter_branding_request", service_id=SERVICE_ONE_ID)

    assert normalize_spaces(page.select_one("h1").text) == "Describe the branding you want"
    assert page.select_one("textarea")["name"] == "branding_request"
    assert normalize_spaces(page.select_one(".page-footer button").text) == "Request new branding"
    assert page.select_one(".govuk-back-link")["href"] == url_for(
        "main.letter_branding_upload_branding",
        service_id=SERVICE_ONE_ID,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "org_id, expected_org_name",
    [
        (ORGANISATION_ID, "Test organisation"),
        (None, "Can’t tell (domain is user.gov.uk)"),
    ],
)
@pytest.mark.parametrize("query_params", [{"from_template": "1234-1234-1234"}, {}])
def test_POST_letter_branding_request_creates_zendesk_ticket(
    client_request,
    service_one,
    mocker,
    mock_get_letter_branding_by_id,
    mock_get_organisation,
    query_params,
    org_id,
    expected_org_name,
):
    mock_send_zendesk = mocker.patch(
        "app.main.views_nl.service_settings.branding.zendesk_client.send_ticket_to_zendesk"
    )
    service_one["organisation"] = org_id

    client_request.post(
        ".letter_branding_request",
        service_id=SERVICE_ONE_ID,
        **query_params,
        _data={
            "branding_request": "Homer Simpson",
        },
        _expected_redirect=(
            url_for("main.view_template", service_id=SERVICE_ONE_ID, template_id=query_params["from_template"])
            if query_params
            else url_for("main.service_settings", service_id=SERVICE_ONE_ID)
        ),
    )

    mock_send_zendesk.assert_called_once()
    zendesk_ticket = mock_send_zendesk.call_args[0][0]
    assert zendesk_ticket.message.split("\n") == [
        f"Organisation: {expected_org_name}",
        "Service: service one",
        "http://localhost/services/596364a0-858e-42c8-9062-a8fe822260eb",
        "",
        "---",
        "Current branding: no",
        "Branding requested:",
        "",
        "Homer Simpson",
    ]
    assert zendesk_ticket.subject == "Letter branding request - service one"
    assert zendesk_ticket.ticket_type == "task"
    assert zendesk_ticket.user_name == "Test User"
    assert zendesk_ticket.user_email == "test@user.gov.uk"
    assert zendesk_ticket.org_id == org_id
    assert zendesk_ticket.org_type == "central"
    assert zendesk_ticket.service_id == SERVICE_ONE_ID
    assert zendesk_ticket.notify_task_type == "notify_task_letter_branding"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_GET_letter_branding_upload_branding_renders_form(
    client_request,
    service_one,
):
    page = client_request.get(
        "main.letter_branding_upload_branding", service_id=SERVICE_ONE_ID, branding_choice="something_else"
    )
    assert "branding is not set up yet" not in normalize_spaces(page.text)

    back_button = page.select_one("a.govuk-back-link")
    form = page.select_one("form")
    submit_button = form.select_one("button")
    file_input = form.select_one("input")
    abandon_flow_link = page.select("main a")[-1]

    assert back_button["href"] == url_for(
        "main.letter_branding_options",
        service_id=SERVICE_ONE_ID,
        branding_choice="something_else",
    )
    assert form["method"] == "post"
    assert "Submit" in submit_button.text
    assert file_input["name"] == "branding"

    assert abandon_flow_link is not None
    assert abandon_flow_link["href"] == url_for(
        "main.letter_branding_request", service_id=SERVICE_ONE_ID, branding_choice="something_else"
    )
    assert abandon_flow_link.text == "I do not have a file to upload"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_GET_letter_branding_upload_branding_renders_form_with_prompt_if_user_clicked_organisation_choice(
    client_request, service_one, organisation_one, mocker
):
    service_one["organisation"] = organisation_one["id"]
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    page = client_request.get(
        "main.letter_branding_upload_branding", service_id=SERVICE_ONE_ID, branding_choice="organisation"
    )
    assert "organisation one branding is not set up yet" in normalize_spaces(page.select_one("main").text)


def test_GET_letter_branding_upload_branding_renders_form_without_prompt_if_user_clicked_something_else_choice(
    client_request, service_one, organisation_one, mocker
):
    service_one["organisation"] = organisation_one["id"]
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    page = client_request.get(
        "main.letter_branding_upload_branding", service_id=SERVICE_ONE_ID, branding_choice="something_else"
    )
    assert "branding is not set up yet" not in normalize_spaces(page.select_one("main").text)


@pytest.mark.parametrize(
    "query_params",
    [
        {"from_template": "1234-1234-1234", "branding_choice": "something_else"},
        {"branding_choice": "something_else"},
    ],
)
def test_GET_letter_branding_upload_branding_passes_from_template_through_to_back_link(
    client_request, service_one, query_params
):
    page = client_request.get(
        "main.letter_branding_upload_branding",
        service_id=SERVICE_ONE_ID,
        **query_params,
    )
    back_link = page.select("a.govuk-back-link")
    assert back_link[0].attrs["href"] == url_for(
        "main.letter_branding_options",
        service_id=SERVICE_ONE_ID,
        **query_params,
    )


@pytest.mark.parametrize(
    "svg_contents, expected_error",
    (
        (
            """
            <svg height="100" width="100">
            <image href="someurlgoeshere" x="0" y="0" height="100" width="100"></image></svg>
        """,
            "This SVG has an embedded raster image in it and will not render well",
        ),
        (
            """
            <svg height="100" width="100">
                <text>Will render differently depending on fonts installed</text>
            </svg>
        """,
            "This SVG has text which has not been converted to paths and may not render well",
        ),
    ),
)
def test_POST_letter_branding_upload_branding_validates_svg_file(
    client_request, svg_contents, expected_error, mock_antivirus_virus_free
):
    page = client_request.post(
        "main.letter_branding_upload_branding",
        service_id=SERVICE_ONE_ID,
        _data={"branding": (BytesIO(svg_contents.encode("utf-8")), "some filename.svg")},
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Upload letter branding"
    assert normalize_spaces(page.select_one(".error-message").text) == expected_error


def test_POST_letter_branding_upload_branding_rejects_non_svg_files(client_request, mock_antivirus_virus_free):
    svg_contents = "<svg> this can actually be an svg we just validate the extension </svg>"
    page = client_request.post(
        "main.letter_branding_upload_branding",
        service_id=SERVICE_ONE_ID,
        _data={"branding": (BytesIO(svg_contents.encode("utf-8")), "some filename.png")},
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Upload letter branding"
    assert normalize_spaces(page.select_one(".error-message").text) == "Branding must be an SVG file"


def test_POST_letter_branding_upload_branding_scans_for_viruses(client_request, mock_antivirus_virus_found):
    svg_contents = "<svg></svg>"
    page = client_request.post(
        "main.letter_branding_upload_branding",
        service_id=SERVICE_ONE_ID,
        _data={"branding": (BytesIO(svg_contents.encode("utf-8")), "some filename.svg")},
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Upload letter branding"
    assert normalize_spaces(page.select_one(".error-message").text) == "This file contains a virus"


def test_POST_letter_branding_upload_branding_redirects_on_success(client_request, mock_antivirus_virus_free, mocker):
    mock_save_temporary = mocker.patch(
        "app.main.views_nl.service_settings.branding.logo_client.save_temporary_logo",
        return_value="temporary.svg",
    )

    svg_contents = "<svg></svg>"

    client_request.post(
        "main.letter_branding_upload_branding",
        service_id=SERVICE_ONE_ID,
        _data={"branding": (BytesIO(svg_contents.encode("utf-8")), "some filename.svg")},
        _expected_redirect=url_for(
            "main.letter_branding_set_name",
            service_id=SERVICE_ONE_ID,
            temp_filename="temporary.svg",
        ),
    )

    mock_save_temporary.assert_called_once_with(
        mocker.ANY,
        logo_type="letter",
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_GET_letter_branding_set_name_renders(client_request, service_one):
    page = client_request.get(
        "main.letter_branding_set_name",
        service_id=SERVICE_ONE_ID,
        temp_filename="temp_something",
    )

    assert page.select_one("main img")["src"] == url_for(
        "no_cookie.letter_branding_preview_image",
        filename="temp_something",
    )

    assert normalize_spaces(page.select_one("h1").text) == "Preview your letter branding"
    assert normalize_spaces(page.select_one("label[for=name]").text) == "Enter the name of your branding"
    assert normalize_spaces(page.select_one("main form button").text) == "Save"
    assert normalize_spaces(page.select_one("div#name-hint").text) == "For example, Department for Education"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_GET_letter_branding_set_name_shows_current_org_in_hint_text(
    client_request,
    service_one,
    mock_get_organisation,
):
    service_one["organisation"] = "1234"

    page = client_request.get(
        "main.letter_branding_set_name",
        service_id=SERVICE_ONE_ID,
        temp_filename="temp_something.svg",
    )
    assert normalize_spaces(page.select_one("div#name-hint").text) == "For example, Test organisation"


def test_GET_letter_branding_set_name_redirects_if_temp_filename_not_provided(client_request):
    client_request.get(
        "main.letter_branding_set_name",
        service_id=SERVICE_ONE_ID,
        branding_choice="something_else",
        _expected_status=302,
        _expected_redirect=url_for(
            "main.letter_branding_upload_branding",
            service_id=SERVICE_ONE_ID,
            branding_choice="something_else",
        ),
    )


def test_POST_letter_branding_set_name_shows_error(client_request, service_one):
    page = client_request.post(
        "main.letter_branding_set_name",
        service_id=SERVICE_ONE_ID,
        temp_filename="temp_example",
        _data={"name": ""},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one("#name-error").text) == "Error: Cannot be empty"


def test_POST_letter_branding_set_name_creates_branding_adds_to_pool_and_redirects(
    client_request,
    service_one,
    mock_create_letter_branding,
    mock_get_organisation,
    mock_update_service,
    fake_uuid,
    mocker,
):
    service_one["organisation"] = ORGANISATION_ID
    mock_flash = mocker.patch("app.main.views_nl.service_settings.branding.flash")
    mock_get_unique_name = mocker.patch(
        "app.main.views_nl.service_settings.branding.letter_branding_client.get_unique_name_for_letter_branding",
        return_value="some unique name",
    )

    mock_should_set_default_org_letter_branding = mocker.patch(
        "app.main.views_nl.service_settings.branding._should_set_default_org_letter_branding", return_value=False
    )
    mock_save_permanent = mocker.patch(
        "app.main.views_nl.service_settings.branding.logo_client.save_permanent_logo", return_value="permanent.svg"
    )

    mock_add_to_branding_pool = mocker.patch(
        "app.organisations_client.add_brandings_to_letter_branding_pool", return_value=None
    )

    client_request.post(
        "main.letter_branding_set_name",
        service_id=SERVICE_ONE_ID,
        temp_filename="temporary.svg",
        branding_choice="something else",
        _data={"name": "some name"},
        _expected_status=302,
        _expected_redirect=url_for("main.service_settings", service_id=SERVICE_ONE_ID),
    )

    mock_get_unique_name.assert_called_once_with("some name")
    mock_create_letter_branding.assert_called_once_with(
        filename="permanent",
        name="some unique name",
        created_by_id=fake_uuid,
    )
    mock_add_to_branding_pool.assert_called_once_with(service_one["organisation"], [fake_uuid])
    mock_should_set_default_org_letter_branding.assert_called_once_with("something else")
    mock_update_service.assert_called_once_with(SERVICE_ONE_ID, letter_branding=fake_uuid)
    mock_flash.assert_called_once_with(
        "You’ve changed your letter branding.",
        "default_with_tick",
    )
    assert mock_save_permanent.call_args_list == [
        mocker.call(
            "temporary.svg",
            logo_type="letter",
            logo_key_extra="some unique name",
        )
    ]


def test_POST_letter_branding_set_name_creates_branding_and_redirects_if_service_has_no_org(
    client_request,
    service_one,
    mock_create_letter_branding,
    mock_get_organisation,
    mock_update_service,
    fake_uuid,
    mocker,
):
    mock_get_unique_name = mocker.patch(
        "app.main.views_nl.service_settings.branding.letter_branding_client.get_unique_name_for_letter_branding",
        return_value="some unique name",
    )
    mock_set_default_org_letter_branding = mocker.patch(
        "app.main.views_nl.service_settings.branding._should_set_default_org_letter_branding"
    )
    mock_save_permanent = mocker.patch(
        "app.main.views_nl.service_settings.branding.logo_client.save_permanent_logo", return_value="permanent.svg"
    )
    mock_add_to_branding_pool = mocker.patch("app.organisations_client.add_brandings_to_letter_branding_pool")

    client_request.post(
        "main.letter_branding_set_name",
        service_id=SERVICE_ONE_ID,
        temp_filename="temporary.svg",
        branding_choice="something else",
        _data={"name": "some name"},
        _expected_status=302,
        _expected_redirect=url_for("main.service_settings", service_id=SERVICE_ONE_ID),
    )

    mock_get_unique_name.assert_called_once_with("some name")
    mock_create_letter_branding.assert_called_once_with(
        filename="permanent",
        name="some unique name",
        created_by_id=fake_uuid,
    )
    assert not mock_add_to_branding_pool.called
    assert not mock_set_default_org_letter_branding.called
    mock_update_service.assert_called_once_with(SERVICE_ONE_ID, letter_branding=fake_uuid)
    assert mock_save_permanent.call_args_list == [
        mocker.call(
            "temporary.svg",
            logo_type="letter",
            logo_key_extra="some unique name",
        )
    ]


def test_POST_letter_branding_set_name_creates_branding_sets_org_default_if_appropriate(
    client_request,
    service_one,
    mock_create_letter_branding,
    mock_update_service,
    mock_get_organisation,
    mock_get_organisation_services,
    mock_update_organisation,
    fake_uuid,
    mocker,
):
    service_one["organisation"] = ORGANISATION_ID
    mock_get_unique_name = mocker.patch(
        "app.main.views_nl.service_settings.branding.letter_branding_client.get_unique_name_for_letter_branding",
    )
    mock_add_to_branding_pool = mocker.patch("app.organisations_client.add_brandings_to_letter_branding_pool")
    mock_save_permanent = mocker.patch("app.main.views_nl.service_settings.branding.logo_client.save_permanent_logo")

    mock_should_set_default_org_letter_branding = mocker.patch(
        "app.main.views_nl.service_settings.branding._should_set_default_org_letter_branding", return_value=True
    )

    client_request.post(
        "main.letter_branding_set_name",
        service_id=SERVICE_ONE_ID,
        temp_filename="temporary.svg",
        branding_choice="organisation",
        _data={"name": "some name"},
        _expected_status=302,
        _expected_redirect=url_for("main.service_settings", service_id=SERVICE_ONE_ID),
    )

    assert mock_get_unique_name.called
    assert mock_create_letter_branding.called
    assert mock_add_to_branding_pool.called
    assert mock_save_permanent.called

    mock_should_set_default_org_letter_branding.assert_called_once_with("organisation")
    mock_update_organisation.assert_called_once_with(
        ORGANISATION_ID, cached_service_ids=ANY, letter_branding_id=fake_uuid
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_letter_branding_option_preview_page_displays_preview_of_chosen_branding(
    service_one, organisation_one, client_request, mocker, mock_get_letter_branding_pool
):
    organisation_one["organisation_type"] = "central"
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    page = client_request.get(
        ".branding_option_preview", service_id=SERVICE_ONE_ID, branding_choice="1234", branding_type="letter"
    )

    assert page.select_one("main img")["src"] == url_for(
        "no_cookie.letter_branding_preview_image",
        branding_style="1234",
    )
    assert page.select_one("main img")["alt"] == "Preview of new letter branding"


def test_letter_branding_option_preview_page_redirects_to_branding_options_page_if_branding_option_not_found(
    service_one, organisation_one, client_request, mocker, mock_get_letter_branding_pool
):
    organisation_one["organisation_type"] = "central"
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    client_request.get(
        ".branding_option_preview",
        service_id=SERVICE_ONE_ID,
        branding_choice="some-unknown-branding-id",
        branding_type="letter",
        _expected_status=302,
        _expected_redirect=url_for("main.letter_branding_options", service_id=SERVICE_ONE_ID),
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_letter_branding_option_preview_changes_letter_branding_when_user_confirms(
    service_one,
    organisation_one,
    client_request,
    no_reply_to_email_addresses,
    single_sms_sender,
    mock_get_letter_branding_pool,
    mock_update_service,
    mock_get_service_data_retention,
    mocker,
):
    organisation_one["organisation_type"] = "central"
    service_one["organisation"] = organisation_one

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    page = client_request.post(
        ".branding_option_preview",
        service_id=SERVICE_ONE_ID,
        branding_choice="1234",
        branding_type="letter",
        _follow_redirects=True,
    )

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        letter_branding="1234",
    )
    assert page.select_one("h1").text == "Settings"
    assert normalize_spaces(page.select_one(".banner-default").text) == "You’ve updated your letter branding"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_letter_branding_nhs_page_displays_preview(
    service_one, organisation_one, client_request, mocker, mock_get_letter_branding_pool
):
    organisation_one["organisation_type"] = "nhs_central"
    service_one["organisation"] = organisation_one
    x = mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    page = client_request.get(
        ".branding_nhs",
        service_id=SERVICE_ONE_ID,
        branding_type="letter",
    )

    assert page.select_one("main img")["src"] == url_for(
        "no_cookie.letter_branding_preview_image",
        branding_style=LetterBranding.NHS_ID,
    )
    assert page.select_one("main img")["alt"] == "Preview of new letter branding"
    assert x.called
    assert mock_get_letter_branding_pool.called


def test_letter_branding_nhs_page_returns_404_if_service_not_nhs(
    service_one, organisation_one, client_request, mocker, mock_get_letter_branding_pool
):
    organisation_one["organisation_type"] = "central"
    service_one["organisation"] = organisation_one
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    client_request.get(
        ".branding_nhs",
        service_id=SERVICE_ONE_ID,
        branding_type="letter",
        branding_choice="some-unknown-branding-id",
        _expected_status=404,
    )


def test_letter_branding_nhs_changes_letter_branding_when_user_confirms(
    service_one,
    organisation_one,
    client_request,
    no_reply_to_email_addresses,
    single_sms_sender,
    mock_get_letter_branding_pool,
    mock_update_service,
    mocker,
):
    organisation_one["organisation_type"] = "nhs_central"
    service_one["organisation"] = organisation_one

    mock_flash = mocker.patch("app.main.views_nl.service_settings.branding.flash")
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    client_request.post(
        ".branding_nhs",
        service_id=SERVICE_ONE_ID,
        branding_type="letter",
        _expected_redirect=url_for("main.service_settings", service_id=SERVICE_ONE_ID),
    )

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        letter_branding=LetterBranding.NHS_ID,
    )
    mock_flash.assert_called_once_with("You’ve updated your letter branding", "default")


@pytest.mark.parametrize("branding_choice", [None, "something_else"])
def test_should_set_default_org_letter_branding_fails_if_branding_choice_is_not_org(
    client_request, mocker, branding_choice
):
    organisation = organisation_json(letter_branding_id=None)
    service = service_json(organisation_id=organisation["id"])
    mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[service, service_json(id_="5678", restricted=True)],
    )

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation)
    g.current_service = Service(service)

    assert _should_set_default_org_letter_branding(branding_choice) is False


def test_should_set_default_org_letter_branding_fails_if_org_already_has_a_default_branding(client_request, mocker):
    organisation = organisation_json(letter_branding_id="12345")
    service = service_json(organisation_id=organisation["id"])
    mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[service, service_json(id_="5678", restricted=True)],
    )

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation)
    g.current_service = Service(service)

    assert _should_set_default_org_letter_branding("organisation") is False


def test_should_set_default_org_letter_branding_fails_if_other_live_services_in_org(client_request, mocker):
    organisation = organisation_json(letter_branding_id=None)
    service = service_json(organisation_id=organisation["id"])
    mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[service, service_json(id_="5678", restricted=False)],
    )

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation)
    g.current_service = Service(service)

    assert _should_set_default_org_letter_branding("organisation") is False


# regardless of whether this service is live, we're only interested in other services with
# different ids when checking for other live services
@pytest.mark.parametrize("is_service_trial", [True, False])
def test_should_set_default_org_letter_branding_succeeds_if_all_conditions_are_met(
    client_request, mocker, is_service_trial
):
    organisation = organisation_json(letter_branding_id=None)
    service = service_json(organisation_id=organisation["id"], restricted=is_service_trial)
    mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[service, service_json(id_="5678", restricted=True)],
    )

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation)
    g.current_service = Service(service)

    assert _should_set_default_org_letter_branding("organisation") is True

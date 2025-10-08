import pytest
from flask import url_for
from freezegun import freeze_time
from notifications_python_client.errors import HTTPError

from tests import find_element_by_tag_and_partial_text, organisation_json, service_json
from tests.app.main.views.test_agreement import MockS3Object
from tests.conftest import (
    ORGANISATION_ID,
    SERVICE_ONE_ID,
    SERVICE_TWO_ID,
    create_active_user_with_permissions,
    create_email_branding,
    create_platform_admin_user,
    normalize_spaces,
)
from tests.utils import RedisClientMock


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_organisation_page_shows_all_organisations(client_request, platform_admin_user, mocker):
    orgs = [
        {"id": "A3", "name": "Test 3", "active": True, "count_of_live_services": 0},
        {"id": "B1", "name": "Test 1", "active": True, "count_of_live_services": 1},
        {"id": "C2", "name": "Test 2", "active": False, "count_of_live_services": 2},
    ]

    get_organisations = mocker.patch("app.models.organisation.AllOrganisations._get_items", return_value=orgs)
    client_request.login(platform_admin_user)
    page = client_request.get(".organisations")

    assert normalize_spaces(page.select_one("h1").text) == "Organisations"

    assert [
        (
            normalize_spaces(link.text),
            normalize_spaces(hint.text),
            link["href"],
        )
        for link, hint in zip(
            page.select(".browse-list-item a"), page.select(".browse-list-item .browse-list-hint"), strict=True
        )
    ] == [
        ("Test 1", "1 live service", url_for("main.organisation_dashboard", org_id="B1")),
        ("Test 2", "2 live services", url_for("main.organisation_dashboard", org_id="C2")),
        ("Test 3", "0 live services", url_for("main.organisation_dashboard", org_id="A3")),
    ]

    archived = page.select_one(".table-field-status-default.heading-medium")
    assert normalize_spaces(archived.text) == "- archived"
    assert normalize_spaces(archived.parent.text) == "Test 2 - archived 2 live services"

    assert normalize_spaces(page.select_one("a.govuk-button--secondary").text) == "New organisation"
    get_organisations.assert_called_once_with()


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_view_organisation_shows_the_correct_organisation(client_request, mocker):
    org = {"id": ORGANISATION_ID, "name": "Test 1", "active": True}
    mocker.patch("app.organisations_client.get_organisation", return_value=org)
    mocker.patch("app.organisations_client.get_services_and_usage", return_value={"services": {}, "updated_at": None})

    page = client_request.get(
        ".organisation_dashboard",
        org_id=ORGANISATION_ID,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Usage"
    assert normalize_spaces(page.select_one(".govuk-hint").text) == "Test 1 has no live services on GOV.UK Notify"
    assert not page.select("a[download]")


def test_page_to_create_new_organisation(
    client_request,
    platform_admin_user,
    mocker,
):
    client_request.login(platform_admin_user)
    page = client_request.get(".add_organisation")

    assert [(input["type"], input["name"], input.get("value")) for input in page.select("input")] == [
        ("text", "name", None),
        ("radio", "organisation_type", "central"),
        ("radio", "organisation_type", "local"),
        ("radio", "organisation_type", "nhs_central"),
        ("radio", "organisation_type", "nhs_local"),
        ("radio", "organisation_type", "nhs_gp"),
        ("radio", "organisation_type", "emergency_service"),
        ("radio", "organisation_type", "school_or_college"),
        ("radio", "organisation_type", "other"),
        ("radio", "crown_status", "crown"),
        ("radio", "crown_status", "non-crown"),
        ("hidden", "csrf_token", mocker.ANY),
    ]


def test_create_new_organisation(
    client_request,
    platform_admin_user,
    mocker,
):
    mock_create_organisation = mocker.patch(
        "app.organisations_client.create_organisation",
        return_value=organisation_json(ORGANISATION_ID),
    )

    client_request.login(platform_admin_user)
    client_request.post(
        ".add_organisation",
        _data={
            "name": "new name",
            "organisation_type": "local",
            "crown_status": "non-crown",
        },
        _expected_redirect=url_for(
            "main.organisation_settings",
            org_id=ORGANISATION_ID,
        ),
    )

    mock_create_organisation.assert_called_once_with(
        name="new name",
        organisation_type="local",
        crown=False,
        agreement_signed=False,
    )


def test_create_new_organisation_validates(
    client_request,
    platform_admin_user,
    mocker,
):
    mock_create_organisation = mocker.patch("app.organisations_client.create_organisation")

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".add_organisation",
        _expected_status=200,
    )
    assert [(normalize_spaces(error.text)) for error in page.select(".govuk-error-message")] == [
        ("Error: Enter an organisation name"),
        ("Error: Select a type of organisation"),
        ("Error: Select yes if the organisation is a Crown body"),
    ]
    assert mock_create_organisation.called is False


@pytest.mark.parametrize(
    "name, error_message",
    [
        ("", "Enter an organisation name"),
        ("a", "Organisation name must include at least 2 letters or numbers"),
        ("a" * 256, "Organisation name cannot be longer than 255 characters"),
    ],
)
def test_create_new_organisation_fails_with_incorrect_input(
    client_request,
    platform_admin_user,
    mocker,
    name,
    error_message,
):
    mock_create_organisation = mocker.patch("app.organisations_client.create_organisation")

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".add_organisation",
        _data={
            "name": name,
            "organisation_type": "local",
            "crown_status": "non-crown",
        },
        _expected_status=200,
    )
    assert mock_create_organisation.called is False
    assert error_message in page.select_one(".govuk-error-message").text


def test_create_new_organisation_fails_with_duplicate_name(
    client_request,
    platform_admin_user,
    mocker,
):
    def _create(**_kwargs):
        json_mock = mocker.Mock(return_value={"message": "Organisation name already exists"})
        resp_mock = mocker.Mock(status_code=400, json=json_mock)
        http_error = HTTPError(response=resp_mock, message="Default message")
        raise http_error

    mocker.patch("app.organisations_client.create_organisation", side_effect=_create)

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".add_organisation",
        _data={
            "name": "Existing org",
            "organisation_type": "local",
            "crown_status": "non-crown",
        },
        _expected_status=200,
    )

    error_message = "This organisation name is already in use"
    assert error_message in page.select_one(".govuk-error-message").text


@pytest.mark.parametrize(
    "organisation_type, organisation, expected_status",
    (
        ("nhs_gp", None, 200),
        ("central", None, 403),
        ("nhs_gp", organisation_json(organisation_type="nhs_gp"), 403),
    ),
)
def test_gps_can_create_own_organisations(
    client_request,
    mocker,
    mock_get_service_organisation,
    service_one,
    organisation_type,
    organisation,
    expected_status,
):
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation)
    service_one["organisation_type"] = organisation_type

    page = client_request.get(
        ".add_organisation_from_gp_service",
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_status,
    )

    if expected_status == 403:
        return

    assert page.select_one("input[type=text]")["name"] == "name"
    assert normalize_spaces(page.select_one("label[for=name]").text) == "What’s your GP surgery called?"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "organisation_type, organisation, expected_status",
    (
        ("nhs_local", None, 200),
        ("nhs_gp", None, 403),
        ("central", None, 403),
        ("nhs_local", organisation_json(organisation_type="nhs_local"), 403),
    ),
)
def test_nhs_local_can_create_own_organisations(
    client_request,
    mocker,
    mock_get_service_organisation,
    service_one,
    organisation_type,
    organisation,
    expected_status,
):
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation)
    mocker.patch(
        "app.models.organisation.AllOrganisations._get_items",
        return_value=[
            organisation_json("t3", "Trust 3", active=False, organisation_type="nhs_local"),
            organisation_json("t2", "Trust 2", organisation_type="nhs_local"),
            organisation_json("t1", "Trust 1", organisation_type="nhs_local"),
            organisation_json("gp1", "GP 1", organisation_type="nhs_gp"),
            organisation_json("c1", "Central 1"),
        ],
    )
    service_one["organisation_type"] = organisation_type

    page = client_request.get(
        ".add_organisation_from_nhs_local_service",
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_status,
    )

    if expected_status == 403:
        return

    assert normalize_spaces(page.select_one("main p").text) == (
        "Which NHS Trust or Integrated Care Board do you work for?"
    )
    assert page.select_one("[data-notify-module=live-search]")["data-targets"] == ".govuk-radios__item"
    assert [
        (normalize_spaces(radio.select_one("label").text), radio.select_one("input")["value"])
        for radio in page.select(".govuk-radios__item")
    ] == [
        ("Trust 1", "t1"),
        ("Trust 2", "t2"),
    ]
    assert normalize_spaces(page.select_one(".js-stick-at-bottom-when-scrolling button").text) == "Continue"


@pytest.mark.parametrize(
    "data, expected_service_name",
    (
        (
            {
                "same_as_service_name": False,
                "name": "Dr. Example",
            },
            "Dr. Example",
        ),
        (
            {
                "same_as_service_name": True,
                "name": "This is ignored",
            },
            "service one",
        ),
    ),
)
def test_gps_can_name_their_organisation(
    client_request,
    mocker,
    service_one,
    mock_update_service_organisation,
    data,
    expected_service_name,
):
    service_one["organisation_type"] = "nhs_gp"
    mock_create_organisation = mocker.patch(
        "app.organisations_client.create_organisation",
        return_value=organisation_json(ORGANISATION_ID),
    )

    client_request.post(
        ".add_organisation_from_gp_service",
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_agreement",
            service_id=SERVICE_ONE_ID,
        ),
    )

    mock_create_organisation.assert_called_once_with(
        name=expected_service_name,
        organisation_type="nhs_gp",
        agreement_signed=False,
        crown=False,
    )
    mock_update_service_organisation.assert_called_once_with(SERVICE_ONE_ID, ORGANISATION_ID)


def test_add_organisation_from_gp_service_when_that_org_name_already_exists(
    client_request,
    mocker,
    service_one,
):
    service_one["organisation_type"] = "nhs_gp"
    mocker.patch(
        "app.organisations_client.create_organisation",
        side_effect=HTTPError(
            response=mocker.Mock(
                status_code=400, json={"result": "error", "message": "Organisation name already exists"}
            ),
            message="Organisation name already exists",
        ),
    )

    page = client_request.post(
        ".add_organisation_from_gp_service",
        service_id=SERVICE_ONE_ID,
        _data={
            "same_as_service_name": True,
            "name": "This is ignored",
        },
        _expected_status=200,
    )

    expected_message = "This organisation name is already in use."
    assert expected_message in page.select_one(".banner-dangerous").text


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "data, expected_error",
    (
        (
            {
                "name": "Dr. Example",
            },
            "Select ‘yes‘ to confirm the name of your GP surgery",
        ),
        (
            {
                "same_as_service_name": False,
                "name": "",
            },
            "Enter the name of your GP surgery",
        ),
    ),
)
def test_validation_of_gps_creating_organisations(
    client_request,
    service_one,
    data,
    expected_error,
):
    service_one["organisation_type"] = "nhs_gp"
    expected_page_header = "Accept our data processing and financial agreement"
    page = client_request.post(
        ".add_organisation_from_gp_service",
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=200,
    )
    assert expected_error in page.select_one(".govuk-error-message, .error-message").text
    assert normalize_spaces(page.select_one("h1[id=page-header]").text) == expected_page_header
    assert normalize_spaces(page.select_one("label[for=same_as_service_name-0]")) == "Yes"
    assert normalize_spaces(page.select_one("label[for=same_as_service_name-1]")) == "No"


def test_nhs_local_assigns_to_selected_organisation(
    client_request,
    mocker,
    service_one,
    mock_get_organisation,
    mock_update_service_organisation,
):
    mocker.patch(
        "app.models.organisation.AllOrganisations._get_items",
        return_value=[
            organisation_json(ORGANISATION_ID, "Trust 1", organisation_type="nhs_local"),
        ],
    )
    service_one["organisation_type"] = "nhs_local"

    client_request.post(
        ".add_organisation_from_nhs_local_service",
        service_id=SERVICE_ONE_ID,
        _data={
            "organisations": ORGANISATION_ID,
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_agreement",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_update_service_organisation.assert_called_once_with(SERVICE_ONE_ID, ORGANISATION_ID)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2020-02-20 20:20")
def test_organisation_services_shows_live_services_and_usage(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
):
    mock = mocker.patch(
        "app.organisations_client.get_services_and_usage",
        return_value={
            "services": [
                {
                    "service_id": SERVICE_ONE_ID,
                    "service_name": "1",
                    "chargeable_billable_sms": 250122,
                    "emails_sent": 13000,
                    "free_sms_limit": 250000,
                    "letter_cost": 30.50,
                    "sms_billable_units": 122,
                    "sms_cost": 0,
                    "sms_remainder": None,
                },
                {
                    "service_id": SERVICE_TWO_ID,
                    "service_name": "5",
                    "chargeable_billable_sms": 0,
                    "emails_sent": 20000,
                    "free_sms_limit": 250000,
                    "letter_cost": 0,
                    "sms_billable_units": 2500,
                    "sms_cost": 42.0,
                    "sms_remainder": None,
                },
            ],
            "updated_at": "2020-02-20T20:00:00.000000+00:00",
        },
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get(".organisation_dashboard", org_id=ORGANISATION_ID)
    mock.assert_called_once_with(ORGANISATION_ID, 2019)

    services = page.select("main h3")
    usage_rows = page.select("main .govuk-grid-column-one-third")
    assert len(services) == 2

    # Totals
    assert normalize_spaces(usage_rows[0].text) == "Emails 33,000 sent"
    assert normalize_spaces(usage_rows[1].text) == "Text messages £42.00 spent"
    assert normalize_spaces(usage_rows[2].text) == "Letters £30.50 spent"

    assert normalize_spaces(services[0].text) == "1"
    assert normalize_spaces(services[1].text) == "5"
    assert services[0].find("a")["href"] == url_for("main.usage", service_id=SERVICE_ONE_ID)

    assert normalize_spaces(usage_rows[3].text) == "13,000 emails sent"
    assert normalize_spaces(usage_rows[4].text) == "122 free text messages sent"
    assert normalize_spaces(usage_rows[5].text) == "£30.50 spent on letters"
    assert services[1].find("a")["href"] == url_for("main.usage", service_id=SERVICE_TWO_ID)
    assert normalize_spaces(usage_rows[6].text) == "20,000 emails sent"
    assert normalize_spaces(usage_rows[7].text) == "£42.00 spent on text messages"
    assert normalize_spaces(usage_rows[8].text) == "£0.00 spent on letters"

    # Ensure there’s no ‘this org has no services message’
    heading_aside = page.select(".heading-aside")
    assert len(heading_aside) == 1
    assert heading_aside[0].text == "Last updated today at 8:00pm"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2020-02-20 20:20")
def test_organisation_services_shows_live_services_and_usage_with_count_of_1(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
):
    mocker.patch(
        "app.organisations_client.get_services_and_usage",
        return_value={
            "services": [
                {
                    "service_id": SERVICE_ONE_ID,
                    "service_name": "1",
                    "chargeable_billable_sms": 1,
                    "emails_sent": 1,
                    "free_sms_limit": 250000,
                    "letter_cost": 0,
                    "sms_billable_units": 1,
                    "sms_cost": 0,
                    "sms_remainder": None,
                },
            ],
            "updated_at": None,
        },
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get(".organisation_dashboard", org_id=ORGANISATION_ID)

    usage_rows = page.select("main .govuk-grid-column-one-third")

    # Totals
    assert normalize_spaces(usage_rows[0].text) == "Emails 1 sent"
    assert normalize_spaces(usage_rows[1].text) == "Text messages £0.00 spent"
    assert normalize_spaces(usage_rows[2].text) == "Letters £0.00 spent"

    assert normalize_spaces(usage_rows[3].text) == "1 email sent"
    assert normalize_spaces(usage_rows[4].text) == "1 free text message sent"
    assert normalize_spaces(usage_rows[5].text) == "£0.00 spent on letters"


@pytest.mark.parametrize(
    "service_usage, expected_css_class",
    (
        (
            {"emails_sent": 999_999_999, "sms_cost": 0, "letter_cost": 0},
            ".big-number-smaller",
        ),
        (
            {"emails_sent": 1_000_000_000, "sms_cost": 0, "letter_cost": 0},
            ".big-number-smallest",
        ),
        (
            {"emails_sent": 0, "sms_cost": 999_999, "letter_cost": 0},
            ".big-number-smaller",
        ),
        (
            {"emails_sent": 0, "sms_cost": 1_000_000, "letter_cost": 0},
            ".big-number-smallest",
        ),
        (
            {"emails_sent": 0, "sms_cost": 0, "letter_cost": 999_999},
            ".big-number-smaller",
        ),
        (
            {"emails_sent": 0, "sms_cost": 0, "letter_cost": 1_000_000},
            ".big-number-smallest",
        ),
    ),
)
@freeze_time("2020-02-20 20:20")
def test_organisation_services_shows_usage_in_correct_font_size(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
    service_usage,
    expected_css_class,
):
    mocker.patch(
        "app.organisations_client.get_services_and_usage",
        return_value={
            "services": [
                service_usage
                | {
                    "service_id": SERVICE_ONE_ID,
                    "service_name": "1",
                    "chargeable_billable_sms": 1,
                    "free_sms_limit": 250000,
                    "sms_billable_units": 1,
                    "sms_remainder": None,
                },
            ],
            "updated_at": None,
        },
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get(".organisation_dashboard", org_id=ORGANISATION_ID)

    usage_totals = page.select_one("main .govuk-grid-row").select(expected_css_class)

    assert len(usage_totals) == 3


@freeze_time("2020-02-20 20:20")
@pytest.mark.parametrize(
    "financial_year, expected_selected",
    (
        (2017, "2017 to 2018 financial year"),
        (2018, "2018 to 2019 financial year"),
        (2019, "2019 to 2020 financial year"),
    ),
)
def test_organisation_services_filters_by_financial_year(
    client_request,
    mock_get_organisation,
    mocker,
    financial_year,
    expected_selected,
):
    mock = mocker.patch(
        "app.organisations_client.get_services_and_usage", return_value={"services": [], "updated_at": None}
    )
    page = client_request.get(
        ".organisation_dashboard",
        org_id=ORGANISATION_ID,
        year=financial_year,
    )
    mock.assert_called_once_with(ORGANISATION_ID, financial_year)
    assert normalize_spaces(page.select_one(".pill").text) == (
        "2019 to 2020 financial year 2018 to 2019 financial year 2017 to 2018 financial year"
    )
    assert normalize_spaces(page.select_one(".pill-item--selected").text) == (expected_selected)


@freeze_time("2020-02-20 20:20")
def test_organisation_services_shows_search_bar(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
):
    mocker.patch(
        "app.organisations_client.get_services_and_usage",
        return_value={
            "services": [
                {
                    "service_id": SERVICE_ONE_ID,
                    "service_name": "Service 1",
                    "chargeable_billable_sms": 250122,
                    "emails_sent": 13000,
                    "free_sms_limit": 250000,
                    "letter_cost": 30.50,
                    "sms_billable_units": 122,
                    "sms_cost": 1.93,
                    "sms_remainder": None,
                },
            ]
            * 8,
            "updated_at": None,
        },
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get(".organisation_dashboard", org_id=ORGANISATION_ID)

    services = page.select(".organisation-service")
    assert len(services) == 8

    assert page.select_one(".live-search")["data-targets"] == ".organisation-service"
    assert [normalize_spaces(service_name.text) for service_name in page.select(".live-search-relevant")] == [
        "Service 1",
        "Service 1",
        "Service 1",
        "Service 1",
        "Service 1",
        "Service 1",
        "Service 1",
        "Service 1",
    ]


@freeze_time("2020-02-20 20:20")
def test_organisation_services_hides_search_bar_for_7_or_fewer_services(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
):
    mocker.patch(
        "app.organisations_client.get_services_and_usage",
        return_value={
            "services": [
                {
                    "service_id": SERVICE_ONE_ID,
                    "service_name": "Service 1",
                    "chargeable_billable_sms": 250122,
                    "emails_sent": 13000,
                    "free_sms_limit": 250000,
                    "letter_cost": 30.50,
                    "sms_billable_units": 122,
                    "sms_cost": 1.93,
                    "sms_remainder": None,
                },
            ]
            * 7,
            "updated_at": None,
        },
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get(".organisation_dashboard", org_id=ORGANISATION_ID)

    services = page.select(".organisation-service")
    assert len(services) == 7
    assert not page.select_one(".live-search")


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2021-11-12 11:09:00.061258")
def test_organisation_services_links_to_downloadable_report(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
):
    mocker.patch(
        "app.organisations_client.get_services_and_usage",
        return_value={
            "services": [
                {
                    "service_id": SERVICE_ONE_ID,
                    "service_name": "Service 1",
                    "chargeable_billable_sms": 250122,
                    "emails_sent": 13000,
                    "free_sms_limit": 250000,
                    "letter_cost": 30.50,
                    "sms_billable_units": 122,
                    "sms_cost": 1.93,
                    "sms_remainder": None,
                },
            ]
            * 2,
            "updated_at": None,
        },
    )
    client_request.login(active_user_with_permissions)
    page = client_request.get(".organisation_dashboard", org_id=ORGANISATION_ID)

    link_to_report = page.select_one("a[download]")
    assert normalize_spaces(link_to_report.text) == "Download this report (CSV)"
    assert link_to_report.attrs["href"] == url_for(
        ".download_organisation_usage_report", org_id=ORGANISATION_ID, selected_year=2021
    )


@freeze_time("2021-11-12 11:09:00.061258")
def test_download_organisation_usage_report(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
):
    mocker.patch(
        "app.organisations_client.get_services_and_usage",
        return_value={
            "services": [
                {
                    "service_id": SERVICE_ONE_ID,
                    "service_name": "Service 1",
                    "chargeable_billable_sms": 22,
                    "emails_sent": 13000,
                    "free_sms_limit": 100,
                    "letter_cost": 30.5,
                    "sms_billable_units": 122,
                    "sms_cost": 1.934,
                    "sms_remainder": 0,
                },
                {
                    "service_id": SERVICE_TWO_ID,
                    "service_name": "Service 1",
                    "chargeable_billable_sms": 222,
                    "emails_sent": 23000,
                    "free_sms_limit": 250000,
                    "letter_cost": 60.5,
                    "sms_billable_units": 322,
                    "sms_cost": 3.935,
                    "sms_remainder": 0,
                },
            ],
            "updated_at": None,
        },
    )
    client_request.login(active_user_with_permissions)
    csv_report = client_request.get(
        ".download_organisation_usage_report", org_id=ORGANISATION_ID, selected_year=2021, _test_page_title=False
    )

    assert csv_report.string == (
        "Service ID,Service Name,Emails sent,Free text message allowance remaining,"
        "Spent on text messages (£),Spent on letters (£)"
        "\r\n596364a0-858e-42c8-9062-a8fe822260eb,Service 1,13000,0,1.93,30.50"
        "\r\n147ad62a-2951-4fa1-9ca0-093cd1a52c52,Service 1,23000,0,3.94,60.50\r\n"
    )


def test_organisation_trial_mode_services_shows_all_non_live_services(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[
            service_json(id_="1", name="1", restricted=False, active=True),  # live
            service_json(id_="2", name="2", restricted=True, active=True),  # trial
            service_json(id_="3", name="3", restricted=False, active=False),  # archived
        ],
    )

    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_trial_mode_services", org_id=ORGANISATION_ID, _test_page_title=False)

    services = page.select(".browse-list-item")
    assert len(services) == 2

    assert normalize_spaces(services[0].text) == "2"
    assert normalize_spaces(services[1].text) == "3"
    assert services[0].find("a")["href"] == url_for("main.service_dashboard", service_id="2")
    assert services[1].find("a")["href"] == url_for("main.service_dashboard", service_id="3")


def test_organisation_trial_mode_services_doesnt_work_if_not_platform_admin(
    client_request,
    mock_get_organisation,
):
    client_request.get(".organisation_trial_mode_services", org_id=ORGANISATION_ID, _expected_status=403)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize("can_approve_own_go_live_requests", (True, False))
def test_manage_org_users_shows_correct_link_next_to_each_user(
    client_request,
    mocker,
    mock_get_users_for_organisation,
    mock_get_invited_users_for_organisation,
    can_approve_own_go_live_requests,
):
    def _get_organisation(org_id):
        return organisation_json(
            org_id,
            {
                "o1": "Org 1",
                "o2": "Org 2",
                "o3": "Org 3",
            }.get(org_id, "Test organisation"),
            can_approve_own_go_live_requests=can_approve_own_go_live_requests,
        )

    mocker.patch("app.organisations_client.get_organisation", side_effect=_get_organisation)

    page = client_request.get(
        ".manage_org_users",
        org_id=ORGANISATION_ID,
    )

    # No banner confirming a user to be deleted shown
    assert not page.select_one(".banner-dangerous")

    users = page.select(".user-list-item")

    if can_approve_own_go_live_requests:
        # The first user is an invited user, so has the link to cancel the invitation.
        # The second two users are active users, so have the link to be removed from the org
        assert normalize_spaces(users[0].text) == (
            "invited_user@test.gov.uk (invited) "
            "Can Make new services live Cancel invitation for invited_user@test.gov.uk"
        )

        assert (
            normalize_spaces(users[1].text)
            == "Test User 1 test@gov.uk Cannot Make new services live Change details for Test User 1 test@gov.uk"
        )
        assert (
            normalize_spaces(users[2].text)
            == "Test User 2 testt@gov.uk Cannot Make new services live Change details for Test User 2 testt@gov.uk"
        )
    else:
        # The first user is an invited user, so has the link to cancel the invitation.
        # The second two users are active users, so have the link to be removed from the org
        assert (
            normalize_spaces(users[0].text)
            == "invited_user@test.gov.uk (invited) Cancel invitation for invited_user@test.gov.uk"
        )

        assert normalize_spaces(users[1].text) == "Test User 1 test@gov.uk Change details for Test User 1 test@gov.uk"
        assert normalize_spaces(users[2].text) == "Test User 2 testt@gov.uk Change details for Test User 2 testt@gov.uk"

    assert users[0].a["href"] == url_for(
        ".cancel_invited_org_user", org_id=ORGANISATION_ID, invited_user_id="73616d70-6c65-4f6f-b267-5f696e766974"
    )
    assert users[1].a["href"] == url_for(".edit_organisation_user", org_id=ORGANISATION_ID, user_id="1234")
    assert users[2].a["href"] == url_for(".edit_organisation_user", org_id=ORGANISATION_ID, user_id="5678")


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_manage_org_users_shows_no_link_for_cancelled_users(
    client_request,
    mock_get_organisation,
    mock_get_users_for_organisation,
    sample_org_invite,
    mocker,
):
    sample_org_invite["status"] = "cancelled"
    mocker.patch("app.models.user.OrganisationInvitedUsers._get_items", return_value=[sample_org_invite])

    page = client_request.get(
        ".manage_org_users",
        org_id=ORGANISATION_ID,
    )
    users = page.select(".user-list-item")

    assert normalize_spaces(users[0].text) == "invited_user@test.gov.uk (cancelled invite)"
    assert not users[0].a


@pytest.mark.skip(reason="[NOTIFYNL] staus doesnt exist on user ???")
@pytest.mark.parametrize(
    "number_of_users",
    (
        pytest.param(7, marks=pytest.mark.xfail),
        pytest.param(8),
    ),
)
def test_manage_org_users_should_show_live_search_if_more_than_7_users(
    client_request,
    mocker,
    mock_get_organisation,
    active_user_with_permissions,
    number_of_users,
):
    mocker.patch(
        "app.models.user.OrganisationInvitedUsers._get_items",
        return_value=[],
    )
    mocker.patch(
        "app.models.user.OrganisationUsers._get_items",
        return_value=[active_user_with_permissions] * number_of_users,
    )

    page = client_request.get(
        ".manage_org_users",
        org_id=ORGANISATION_ID,
    )

    assert page.select_one("div[data-notify-module=live-search]")["data-targets"] == ".user-list-item"
    assert len(page.select(".user-list-item")) == number_of_users

    textbox = page.select_one("[data-notify-module=autofocus] .govuk-input")
    assert "value" not in textbox
    assert textbox["name"] == "search"
    # data-notify-module=autofocus is set on a containing element so it
    # shouldn’t also be set on the textbox itself
    assert "data-notify-module" not in textbox
    assert not page.select_one("[data-force-focus]")
    assert textbox["class"] == [
        "govuk-input",
        "govuk-!-width-full",
    ]
    assert normalize_spaces(page.select_one("label[for=search]").text) == "Search by name or email address"


def test_remove_user_from_organisation_makes_api_request_to_remove_user(
    client_request,
    mocker,
    mock_get_organisation,
    fake_uuid,
):
    mock_remove_user = mocker.patch("app.organisations_client.remove_user_from_organisation")

    client_request.post(
        ".remove_user_from_organisation",
        org_id=ORGANISATION_ID,
        user_id=fake_uuid,
        _expected_redirect=url_for(
            "main.show_accounts_or_dashboard",
        ),
    )

    mock_remove_user.assert_called_with(ORGANISATION_ID, fake_uuid)


def test_organisation_settings_platform_admin_only(client_request, mock_get_organisation, organisation_one):
    client_request.get(
        ".organisation_settings",
        org_id=organisation_one["id"],
        _expected_status=403,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_organisation_settings_for_platform_admin(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mock_get_empty_email_branding_pool,
    mock_get_empty_letter_branding_pool,
    organisation_one,
):
    expected_rows = [
        "Name Test organisation Change organisation name",
        "Sector Central government Change sector for the organisation",
        "Crown organisation Yes Change organisation crown status",
        (
            "Data processing and financial agreement "
            "Not signed Change data processing and financial agreement for the organisation"
        ),
        "Request to go live notes None Change go live notes for the organisation",
        "Can approve own go-live requests No Change whether this organisation can approve its own go-live requests",
        "Users can ask to join services No Change whether this users can ask to join services in this organisation",
        "Billing details None Change billing details for the organisation",
        "Notes None Change the notes for the organisation",
        "Email branding options GOV.UK Default Manage email branding options for the organisation",
        "Letter branding options No branding Default Manage letter branding options for the organisation",
        "Known email domains None Change known email domains for the organisation",
    ]

    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_settings", org_id=organisation_one["id"])

    assert page.select_one("h1").text == "Settings"
    rows = page.select(".govuk-summary-list__row")
    assert len(rows) == len(expected_rows)
    for index, row in enumerate(expected_rows):
        assert row == " ".join(rows[index].text.split())
    mock_get_organisation.assert_called_with(organisation_one["id"])


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_organisation_settings_table_shows_email_branding_pool(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mock_get_email_branding_pool,
    mock_get_letter_branding_pool,
    organisation_one,
):
    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_settings", org_id=organisation_one["id"])

    email_branding_options_row = page.select(".govuk-summary-list__row")[9]

    assert normalize_spaces(email_branding_options_row.text) == (
        "Email branding options "
        "GOV.UK Default "
        "Email branding name 1 "
        "Email branding name 2 "
        "Manage email branding options for the organisation"
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_organisation_settings_table_shows_letter_branding_pool(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mock_get_email_branding_pool,
    mock_get_letter_branding_pool,
    organisation_one,
):
    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_settings", org_id=organisation_one["id"])

    letter_branding_options_row = find_element_by_tag_and_partial_text(
        page, ".govuk-summary-list__row", "Letter branding options"
    )

    assert normalize_spaces(letter_branding_options_row.text) == (
        "Letter branding options "
        "No branding Default "
        "Cabinet Office "
        "Department for Education "
        "Government Digital Service "
        "Manage letter branding options for the organisation"
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_organisation_settings_table_shows_letter_branding_pool_with_brand_as_default(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mock_get_empty_email_branding_pool,
    mock_get_letter_branding_pool,
    organisation_one,
    mocker,
):
    organisation_one["letter_branding_id"] = "5678"
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    mocker.patch(
        "app.models.branding.letter_branding_client.get_letter_branding",
        return_value={
            "id": "5678",
            "name": "Department for Education",
            "filename": "dfe",
        },
    )

    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_settings", org_id=organisation_one["id"])

    letter_branding_options_row = find_element_by_tag_and_partial_text(
        page, ".govuk-summary-list__row", "Letter branding options"
    )

    assert normalize_spaces(letter_branding_options_row.text) == (
        "Letter branding options "
        "Department for Education Default "
        "Cabinet Office "
        "Government Digital Service "
        "Manage letter branding options for the organisation"
    )
    # check we're showing the styling for when there are multiple items in the pool
    assert letter_branding_options_row.select_one("div.govuk-\\!-margin-bottom-3")


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_organisation_settings_table_shows_email_branding_pool_non_govuk_default(
    client_request,
    mocker,
    mock_get_email_branding_pool,
    mock_get_letter_branding_pool,
    mock_get_email_branding,
    platform_admin_user,
    organisation_one,
):
    email_branding_pool = mock_get_email_branding_pool(organisation_one["id"])
    organisation_one["email_branding_id"] = email_branding_pool[0]["id"]
    email_branding = create_email_branding(
        email_branding_pool[0]["id"],
        non_standard_values={
            "name": email_branding_pool[0]["name"],
            "text": email_branding_pool[0]["text"],
        },
    )

    with (
        mocker.patch("app.organisations_client.get_organisation", side_effect=lambda *args, **kwargs: organisation_one),
        mocker.patch(
            "app.email_branding_client.get_email_branding", side_effect=lambda *args, **kwargs: email_branding
        ),
    ):
        client_request.login(platform_admin_user)
        page = client_request.get(".organisation_settings", org_id=organisation_one["id"])

    email_branding_options_row = page.select(".govuk-summary-list__row")[9]

    assert normalize_spaces(email_branding_options_row.text) == (
        "Email branding options "
        "Email branding name 1 Default "
        "Email branding name 2 "
        "Manage email branding options for the organisation"
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_organisation_settings_table_shows_email_branding_pool_govuk_default(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mock_get_empty_email_branding_pool,
    mock_get_letter_branding_pool,
    organisation_one,
):
    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_settings", org_id=organisation_one["id"])

    email_branding_options_row = page.select(".govuk-summary-list__row")[9]

    assert normalize_spaces(email_branding_options_row.text) == (
        "Email branding options GOV.UK Default Manage email branding options for the organisation"
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_organisation_settings_shows_delete_link(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
    mock_get_email_branding_pool,
    mock_get_letter_branding_pool,
):
    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_settings", org_id=organisation_one["id"])

    delete_link = page.select(".page-footer-link a")[0]
    assert normalize_spaces(delete_link.text) == "Delete this organisation"
    assert delete_link["href"] == url_for(
        "main.archive_organisation",
        org_id=organisation_one["id"],
    )


def test_organisation_settings_does_not_show_delete_link_for_archived_organisations(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_email_branding_pool,
    mock_get_letter_branding_pool,
    mocker,
):
    organisation_one["active"] = False
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_settings", org_id=organisation_one["id"])

    assert not page.select(".page-footer-link a")


def test_archive_organisation_is_platform_admin_only(
    client_request,
    organisation_one,
    mock_get_organisation,
    mocker,
):
    client_request.get("main.archive_organisation", org_id=organisation_one["id"], _expected_status=403)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_archive_organisation_prompts_user(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_email_branding_pool,
    mock_get_letter_branding_pool,
    mocker,
):
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    client_request.login(platform_admin_user)
    delete_page = client_request.get(
        "main.archive_organisation",
        org_id=organisation_one["id"],
    )
    assert normalize_spaces(delete_page.select_one(".banner-dangerous").text) == (
        "Are you sure you want to delete ‘organisation one’? There’s no way to undo this. Yes, delete"
    )


@pytest.mark.parametrize("method", ["get", "post"])
def test_archive_organisation_gives_403_for_inactive_orgs(
    client_request,
    platform_admin_user,
    organisation_one,
    mocker,
    method,
):
    organisation_one["active"] = False
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    client_request.login(platform_admin_user)

    getattr(client_request, method)("main.archive_organisation", org_id=organisation_one["id"], _expected_status=403)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_archive_organisation_after_confirmation(
    client_request,
    platform_admin_user,
    organisation_one,
    mocker,
    mock_get_organisation,
    mock_get_organisations,
    mock_get_organisations_and_services_for_user,
    mock_get_service_and_organisation_counts,
    mock_get_organisation_by_domain,
):
    mock_api = mocker.patch("app.organisations_client.post")
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete", new_callable=RedisClientMock)

    client_request.login(platform_admin_user)
    page = client_request.post("main.archive_organisation", org_id=organisation_one["id"], _follow_redirects=True)

    mock_api.assert_called_once_with(url=f"/organisations/{organisation_one['id']}/archive", data=None)
    assert normalize_spaces(page.select_one("h1").text) == "Your services"
    assert normalize_spaces(page.select_one(".banner-default-with-tick").text) == "‘Test organisation’ was deleted"
    mock_redis_delete.assert_called_with_args(
        f"organisation-{organisation_one['id']}-name",
        "domains",
        "organisations",
    )


@pytest.mark.parametrize(
    "error_message",
    [
        "Cannot archive an organisation with active services",
        "Cannot archive an organisation with team members or invited team members",
    ],
)
def test_archive_organisation_does_not_allow_orgs_with_team_members_or_services_to_be_archived(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
    mock_get_email_branding_pool,
    mock_get_letter_branding_pool,
    mock_get_users_for_organisation,
    mock_get_invited_users_for_organisation,
    mocker,
    error_message,
):
    mocker.patch(
        "app.organisations_client.archive_organisation",
        side_effect=HTTPError(
            response=mocker.Mock(status_code=400, json={"result": "error", "message": error_message}),
            message=error_message,
        ),
    )
    client_request.login(platform_admin_user)
    page = client_request.post(
        "main.archive_organisation",
        org_id=organisation_one["id"],
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one("div.banner-dangerous").text) == error_message


@pytest.mark.parametrize(
    "endpoint, expected_options, expected_selected",
    (
        (
            ".edit_organisation_type",
            (
                {"value": "central", "label": "Central government"},
                {"value": "local", "label": "Local government"},
                {"value": "nhs_central", "label": "NHS – central government agency or public body"},
                {"value": "nhs_local", "label": "NHS Trust or Integrated Care Board"},
                {"value": "nhs_gp", "label": "GP surgery"},
                {"value": "emergency_service", "label": "Emergency service"},
                {"value": "school_or_college", "label": "School or college"},
                {"value": "other", "label": "Other"},
            ),
            "central",
        ),
        (
            ".edit_organisation_crown_status",
            (
                {"value": "crown", "label": "Yes"},
                {"value": "non-crown", "label": "No"},
                {"value": "unknown", "label": "Not sure"},
            ),
            "crown",
        ),
        (
            ".edit_organisation_agreement",
            (
                {
                    "value": "yes",
                    "label": "Yes",
                    "hint": "Users will be told their organisation has already signed the agreement",
                },
                {
                    "value": "no",
                    "label": "No",
                    "hint": "Users will be prompted to sign the agreement before they can go live",
                },
                {
                    "value": "unknown",
                    "label": "No (but we have some service-specific agreements in place)",
                    "hint": "Users will not be prompted to sign the agreement",
                },
            ),
            "no",
        ),
    ),
)
@pytest.mark.parametrize(
    "user",
    (
        pytest.param(
            create_platform_admin_user(),
        ),
        pytest.param(create_active_user_with_permissions(), marks=pytest.mark.xfail),
    ),
)
def test_view_organisation_settings(
    client_request,
    organisation_one,
    mock_get_organisation,
    endpoint,
    expected_options,
    expected_selected,
    user,
):
    client_request.login(user)

    page = client_request.get(endpoint, org_id=organisation_one["id"])

    radios = page.select("input[type=radio]")

    for index, option in enumerate(expected_options):
        option_values = {
            "value": radios[index]["value"],
            "label": normalize_spaces(page.select_one(f"label[for={radios[index]['id']}]").text),
        }
        if "hint" in option:
            option_values["hint"] = normalize_spaces(
                page.select_one(f"label[for={radios[index]['id']}] + .govuk-hint").text
            )
        assert option_values == option

    if expected_selected:
        assert page.select_one("input[checked]")["value"] == expected_selected
    else:
        assert not page.select_one("input[checked]")


@pytest.mark.parametrize(
    "endpoint, post_data, expected_persisted",
    (
        (
            ".edit_organisation_type",
            {"organisation_type": "central"},
            {"cached_service_ids": [], "organisation_type": "central"},
        ),
        (
            ".edit_organisation_type",
            {"organisation_type": "local"},
            {"cached_service_ids": [], "organisation_type": "local"},
        ),
        (
            ".edit_organisation_type",
            {"organisation_type": "nhs_local"},
            {"cached_service_ids": [], "organisation_type": "nhs_local"},
        ),
        (
            ".edit_organisation_crown_status",
            {"crown_status": "crown"},
            {"cached_service_ids": [], "crown": True},
        ),
        (
            ".edit_organisation_crown_status",
            {"crown_status": "non-crown"},
            {"cached_service_ids": [], "crown": False},
        ),
        (
            ".edit_organisation_crown_status",
            {"crown_status": "unknown"},
            {"cached_service_ids": [], "crown": None},
        ),
        (
            ".edit_organisation_agreement",
            {"agreement_signed": "yes"},
            {"agreement_signed": True},
        ),
        (
            ".edit_organisation_agreement",
            {"agreement_signed": "no"},
            {"agreement_signed": False},
        ),
        (
            ".edit_organisation_agreement",
            {"agreement_signed": "unknown"},
            {"agreement_signed": None},
        ),
    ),
)
@pytest.mark.parametrize(
    "user",
    (
        pytest.param(
            create_platform_admin_user(),
        ),
        pytest.param(create_active_user_with_permissions(), marks=pytest.mark.xfail),
    ),
)
def test_update_organisation_settings(
    client_request,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
    endpoint,
    post_data,
    expected_persisted,
    user,
    mocker,
):
    mocker.patch("app.organisations_client.get_organisation_services", return_value=[])
    client_request.login(user)

    client_request.post(
        endpoint,
        org_id=organisation_one["id"],
        _data=post_data,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.organisation_settings",
            org_id=organisation_one["id"],
        ),
    )

    mock_update_organisation.assert_called_once_with(
        organisation_one["id"],
        **expected_persisted,
    )


def test_update_organisation_sector_sends_service_id_data_to_api_client(
    client_request,
    mock_get_organisation,
    organisation_one,
    mock_get_organisation_services,
    mock_update_organisation,
    platform_admin_user,
):
    client_request.login(platform_admin_user)

    client_request.post(
        "main.edit_organisation_type",
        org_id=organisation_one["id"],
        _data={"organisation_type": "central"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.organisation_settings",
            org_id=organisation_one["id"],
        ),
    )

    mock_update_organisation.assert_called_once_with(
        organisation_one["id"], cached_service_ids=["12345", "67890", SERVICE_ONE_ID], organisation_type="central"
    )


@pytest.mark.parametrize(
    "user",
    (
        pytest.param(
            create_platform_admin_user(),
        ),
        pytest.param(create_active_user_with_permissions(), marks=pytest.mark.xfail),
    ),
)
def test_view_organisation_domains(
    client_request,
    user,
    mocker,
):
    client_request.login(user)

    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            domains=["example.gov.uk", "test.example.gov.uk"],
        ),
    )

    page = client_request.get(
        "main.edit_organisation_domains",
        org_id=ORGANISATION_ID,
    )

    assert [textbox.get("value") for textbox in page.select("input[type=text]")] == [
        "example.gov.uk",
        "test.example.gov.uk",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ]


@pytest.mark.parametrize(
    "post_data, expected_persisted",
    (
        (
            {
                "domains-0": "example.gov.uk",
                "domains-2": "example.gov.uk",
                "domains-3": "EXAMPLE.GOV.UK",
                "domains-5": "test.gov.uk",
            },
            {
                "domains": [
                    "example.gov.uk",
                    "test.gov.uk",
                ]
            },
        ),
        (
            {
                "domains-0": "",
                "domains-1": "",
                "domains-2": "",
            },
            {"domains": []},
        ),
    ),
)
@pytest.mark.parametrize(
    "user",
    (
        pytest.param(
            create_platform_admin_user(),
        ),
        pytest.param(create_active_user_with_permissions(), marks=pytest.mark.xfail),
    ),
)
def test_update_organisation_domains(
    client_request,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
    post_data,
    expected_persisted,
    user,
):
    client_request.login(user)

    client_request.post(
        "main.edit_organisation_domains",
        org_id=ORGANISATION_ID,
        _data=post_data,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.organisation_settings",
            org_id=organisation_one["id"],
        ),
    )

    mock_update_organisation.assert_called_once_with(
        ORGANISATION_ID,
        **expected_persisted,
    )


def test_update_organisation_domains_when_domain_already_exists(
    client_request,
    organisation_one,
    mock_get_organisation,
    mocker,
):
    user = create_platform_admin_user()
    client_request.login(user)

    mocker.patch(
        "app.organisations_client.update_organisation",
        side_effect=HTTPError(
            response=mocker.Mock(status_code=400, json={"result": "error", "message": "Domain already exists"}),
            message="Domain already exists",
        ),
    )

    response = client_request.post(
        "main.edit_organisation_domains",
        org_id=ORGANISATION_ID,
        _data={
            "domains": [
                "example.gov.uk",
            ]
        },
        _expected_status=200,
    )

    assert response.select_one("div.banner-dangerous").text.strip() == "This domain is already in use"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_update_organisation_domains_with_more_than_just_domain(
    client_request,
    mocker,
):
    user = create_platform_admin_user()
    client_request.login(user)

    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            domains=["test.example.gov.uk"],
        ),
    )

    page = client_request.post(
        "main.edit_organisation_domains",
        org_id=ORGANISATION_ID,
        _data={
            "domains-0": "test@example.gov.uk",
            "domains-1": "example.gov.uk",
            "domains-2": "@example.gov.uk",
        },
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one(".govuk-error-summary__title").text) == ("There is a problem")

    error_summary_links = page.select(".govuk-error-summary__list a")

    assert normalize_spaces(error_summary_links[0].text) == "Domain name 1 cannot contain @"
    assert normalize_spaces(error_summary_links[0]["href"]) == "#domains-1"

    assert normalize_spaces(error_summary_links[1].text) == "Domain name 3 cannot contain @"
    assert normalize_spaces(error_summary_links[1]["href"]) == "#domains-3"

    assert [normalize_spaces(error_link.text) for error_link in page.select(".govuk-error-summary__list a")] == [
        "Domain name 1 cannot contain @",
        "Domain name 3 cannot contain @",
    ]

    assert [field["value"] for field in page.select("input[type=text][value]")] == [
        "test@example.gov.uk",
        "example.gov.uk",
        "@example.gov.uk",
    ]


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "domain",
    (
        "nhs.net",
        "NHS.NET",
        "nhs.uk",
        pytest.param(
            "example.nhs.uk",
            marks=pytest.mark.xfail(reason="Subdomains still allowed"),
        ),
    ),
)
def test_update_organisation_domains_nhs_domains(
    client_request,
    mock_get_organisation,
    domain,
):
    user = create_platform_admin_user()
    client_request.login(user)

    page = client_request.post(
        "main.edit_organisation_domains",
        org_id=ORGANISATION_ID,
        _data={"domains-0": domain},
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one(".govuk-error-summary__title").text) == ("There is a problem")

    if domain == "NHS.NET":  # NHS.NET fails by being nhs.net (lowercased) so is announced as such
        failed_domain = domain.lower()
    else:
        failed_domain = domain

    assert (
        normalize_spaces(page.select_one(".govuk-error-summary__list li:first-of-type a").text)
        == f"Domain name 1 cannot be ‘{failed_domain}’"
    )

    assert (
        normalize_spaces(page.select_one(".list-entry:first-of-type .govuk-error-message").text)
        == f"Error: Cannot be ‘{failed_domain}’"
    )

    assert [field["value"] for field in page.select("input[type=text][value]")] == [
        domain,
    ]


def test_update_organisation_name(
    client_request,
    platform_admin_user,
    fake_uuid,
    mock_get_organisation,
    mock_update_organisation,
):
    client_request.login(platform_admin_user)
    client_request.post(
        ".edit_organisation_name",
        org_id=fake_uuid,
        _data={"name": "TestNewOrgName"},
        _expected_redirect=url_for(
            ".organisation_settings",
            org_id=fake_uuid,
        ),
    )
    mock_update_organisation.assert_called_once_with(
        fake_uuid,
        name="TestNewOrgName",
        cached_service_ids=None,
    )


@pytest.mark.parametrize(
    "name, error_message",
    [
        ("", "Enter your organisation name"),
        ("a", "Organisation name must include at least 2 letters or numbers"),
        ("a" * 256, "Organisation name cannot be longer than 255 characters"),
    ],
)
def test_update_organisation_with_incorrect_input(
    client_request, platform_admin_user, organisation_one, mock_get_organisation, name, error_message
):
    client_request.login(platform_admin_user)
    page = client_request.post(
        ".edit_organisation_name",
        org_id=organisation_one["id"],
        _data={"name": name},
        _expected_status=200,
    )
    assert error_message in page.select_one(".govuk-error-message").text


def test_update_organisation_with_non_unique_name(
    client_request,
    platform_admin_user,
    fake_uuid,
    mock_get_organisation,
    mocker,
):
    mocker.patch(
        "app.organisations_client.update_organisation",
        side_effect=HTTPError(
            response=mocker.Mock(
                status_code=400, json={"result": "error", "message": "Organisation name already exists"}
            ),
            message="Organisation name already exists",
        ),
    )
    client_request.login(platform_admin_user)
    page = client_request.post(
        ".edit_organisation_name",
        org_id=fake_uuid,
        _data={"name": "TestNewOrgName"},
        _expected_status=200,
    )

    assert "This organisation name is already in use" in page.select_one(".govuk-error-message").text


def test_get_edit_organisation_go_live_notes_page(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    organisation_one,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        ".edit_organisation_go_live_notes",
        org_id=organisation_one["id"],
    )
    assert page.select_one("textarea", id="request_to_go_live_notes")


@pytest.mark.parametrize("input_note,saved_note", [("Needs permission", "Needs permission"), ("  ", None)])
def test_post_edit_organisation_go_live_notes_updates_go_live_notes(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mock_update_organisation,
    organisation_one,
    input_note,
    saved_note,
):
    client_request.login(platform_admin_user)
    client_request.post(
        ".edit_organisation_go_live_notes",
        org_id=organisation_one["id"],
        _data={"request_to_go_live_notes": input_note},
        _expected_redirect=url_for(
            ".organisation_settings",
            org_id=organisation_one["id"],
        ),
    )
    mock_update_organisation.assert_called_once_with(organisation_one["id"], request_to_go_live_notes=saved_note)


def test_organisation_settings_links_to_edit_organisation_notes_page(
    mock_get_organisation,
    mock_get_email_branding_pool,
    mock_get_letter_branding_pool,
    organisation_one,
    client_request,
    platform_admin_user,
    mocker,
):
    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_settings", org_id=organisation_one["id"])

    assert page.select(".govuk-summary-list__actions a")[4]["href"] == url_for(
        ".edit_organisation_go_live_notes",
        org_id=organisation_one["id"],
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_view_edit_organisation_notes(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.edit_organisation_notes",
        org_id=organisation_one["id"],
    )
    assert page.select_one("h1").text == "Edit organisation notes"
    assert page.select_one(".govuk-label").text.strip() == "Notes"
    assert page.select_one("textarea").attrs["name"] == "notes"


def test_update_organisation_notes(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.edit_organisation_notes",
        org_id=organisation_one["id"],
        _data={"notes": "Very fluffy"},
        _expected_redirect=url_for(
            "main.organisation_settings",
            org_id=organisation_one["id"],
        ),
    )
    mock_update_organisation.assert_called_with(organisation_one["id"], cached_service_ids=None, notes="Very fluffy")


def test_update_organisation_notes_errors_when_user_not_platform_admin(
    client_request,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
):
    client_request.post(
        "main.edit_organisation_notes",
        org_id=organisation_one["id"],
        _data={"notes": "Very fluffy"},
        _expected_status=403,
    )


def test_organisation_settings_links_to_edit_can_approve_own_go_live_request(
    mock_get_organisation,
    mock_get_email_branding_pool,
    mock_get_letter_branding_pool,
    organisation_one,
    client_request,
    platform_admin_user,
    mocker,
):
    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_settings", org_id=organisation_one["id"])

    assert page.select(".govuk-summary-list__actions a")[5]["href"] == url_for(
        ".edit_organisation_can_approve_own_go_live_requests",
        org_id=organisation_one["id"],
    )


def test_organisation_settings_links_to_edit_can_ask_to_join_a_service(
    mock_get_organisation,
    mock_get_email_branding_pool,
    mock_get_letter_branding_pool,
    organisation_one,
    client_request,
    platform_admin_user,
    mocker,
):
    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_settings", org_id=organisation_one["id"])

    assert page.select(".govuk-summary-list__actions a")[6]["href"] == url_for(
        ".edit_organisation_can_ask_to_join_a_service",
        org_id=organisation_one["id"],
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "value_from_api, expected_checked_value, expected_label, permission_list",
    (
        (True, "True", "Yes", ["can_ask_to_join_a_service"]),
        (False, "False", "No", []),
    ),
)
def test_get_can_ask_to_join_a_service(
    client_request,
    fake_uuid,
    platform_admin_user,
    value_from_api,
    expected_checked_value,
    expected_label,
    permission_list,
    mocker,
):
    client_request.login(platform_admin_user)

    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            can_ask_to_join_a_service=value_from_api,
            permissions=permission_list,
        ),
    )

    page = client_request.get(
        "main.edit_organisation_can_ask_to_join_a_service",
        org_id=fake_uuid,
    )
    checked_radio = page.select_one("input[checked]")
    assert checked_radio["value"] == expected_checked_value
    assert normalize_spaces(page.select_one(f"label[for={checked_radio['id']}]").text) == expected_label


@pytest.mark.parametrize(
    "post_data, expected_parameter",
    (
        (
            {"enabled": "True"},
            ["can_ask_to_join_a_service"],
        ),
        (
            {"enabled": "False"},
            [],
        ),
    ),
)
def test_add_delete_can_ask_to_join_a_service(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
    post_data,
    expected_parameter,
):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.edit_organisation_can_ask_to_join_a_service",
        org_id=organisation_one["id"],
        _data=post_data,
        _expected_redirect=url_for(
            "main.organisation_settings",
            org_id=organisation_one["id"],
        ),
    )

    mock_update_organisation.assert_called_with(
        organisation_one["id"],
        cached_service_ids=None,
        permissions=expected_parameter,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "value_from_api, expected_checked_value, expected_label",
    (
        (True, "True", "Yes"),
        (False, "False", "No"),
    ),
)
def test_get_can_approve_own_go_live_requests(
    client_request,
    fake_uuid,
    platform_admin_user,
    value_from_api,
    expected_checked_value,
    expected_label,
    mocker,
):
    client_request.login(platform_admin_user)

    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            can_approve_own_go_live_requests=value_from_api,
        ),
    )

    page = client_request.get(
        "main.edit_organisation_can_approve_own_go_live_requests",
        org_id=fake_uuid,
    )
    checked_radio = page.select_one("input[checked]")
    assert checked_radio["value"] == expected_checked_value
    assert normalize_spaces(page.select_one(f"label[for={checked_radio['id']}]").text) == expected_label


@pytest.mark.parametrize(
    "post_data, expected_value_sent_to_api",
    (
        (
            {"enabled": "True"},
            True,
        ),
        (
            {"enabled": "False"},
            False,
        ),
    ),
)
def test_update_can_approve_own_go_live_requests(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
    post_data,
    expected_value_sent_to_api,
):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.edit_organisation_can_approve_own_go_live_requests",
        org_id=organisation_one["id"],
        _data=post_data,
        _expected_redirect=url_for(
            "main.organisation_settings",
            org_id=organisation_one["id"],
        ),
    )
    mock_update_organisation.assert_called_with(
        organisation_one["id"], cached_service_ids=None, can_approve_own_go_live_requests=expected_value_sent_to_api
    )


@pytest.mark.parametrize("method", ("get", "post"))
def test_update_can_approve_own_go_live_requests_errors_when_user_not_platform_admin(
    client_request,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
    method,
):
    getattr(client_request, method)(
        "main.edit_organisation_can_approve_own_go_live_requests",
        org_id=organisation_one["id"],
        _expected_status=403,
    )


def test_update_organisation_notes_doesnt_call_api_when_notes_dont_change(
    client_request, platform_admin_user, organisation_one, mock_update_organisation, mocker
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=organisation_one["id"], name="Test Org", notes="Very fluffy"),
    )
    client_request.login(platform_admin_user)
    client_request.post(
        "main.edit_organisation_notes",
        org_id=organisation_one["id"],
        _data={"notes": "Very fluffy"},
        _expected_redirect=url_for(
            "main.organisation_settings",
            org_id=organisation_one["id"],
        ),
    )
    assert not mock_update_organisation.called


def test_organisation_settings_links_to_edit_organisation_billing_details_page(
    mock_get_organisation,
    mock_get_email_branding_pool,
    mock_get_letter_branding_pool,
    organisation_one,
    client_request,
    platform_admin_user,
    mocker,
):
    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_settings", org_id=organisation_one["id"])
    assert len(page.select(f"""a[href="/organisations/{organisation_one["id"]}/settings/edit-billing-details"]""")) == 1


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_view_edit_organisation_billing_details(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.edit_organisation_billing_details",
        org_id=organisation_one["id"],
    )
    assert page.select_one("h1").text == "Edit organisation billing details"

    assert [label.text.strip() for label in page.select("label.govuk-label") + page.select("label.form-label")] == [
        "Contact names",
        "Contact email addresses",
        "Reference",
        "Purchase order number",
        "Notes",
    ]

    assert [
        form_element["name"]
        for form_element in page.select("input.govuk-input.govuk-\\!-width-full") + page.select("textarea")
    ] == [
        "billing_contact_names",
        "billing_contact_email_addresses",
        "billing_reference",
        "purchase_order_number",
        "notes",
    ]


def test_update_organisation_billing_details(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.edit_organisation_billing_details",
        org_id=organisation_one["id"],
        _data={
            "billing_contact_email_addresses": "accounts@fluff.gov.uk",
            "billing_contact_names": "Flannellette von Fluff",
            "billing_reference": "",
            "purchase_order_number": "PO1234",
            "notes": "very fluffy, give extra allowance",
        },
        _expected_redirect=url_for(
            "main.organisation_settings",
            org_id=organisation_one["id"],
        ),
    )
    mock_update_organisation.assert_called_with(
        organisation_one["id"],
        cached_service_ids=None,
        billing_contact_email_addresses="accounts@fluff.gov.uk",
        billing_contact_names="Flannellette von Fluff",
        billing_reference="",
        purchase_order_number="PO1234",
        notes="very fluffy, give extra allowance",
    )


def test_update_organisation_billing_details_errors_when_user_not_platform_admin(
    client_request,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
):
    client_request.post(
        "main.edit_organisation_billing_details",
        org_id=organisation_one["id"],
        _data={"notes": "Very fluffy"},
        _expected_status=403,
    )


def test_organisation_billing_page_not_accessible_if_not_platform_admin(
    client_request,
    mock_get_organisation,
):
    client_request.get(".organisation_billing", org_id=ORGANISATION_ID, _expected_status=403)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "signed_by_id, signed_by_name, expected_signatory",
    [
        ("1234", None, "Test User"),
        (None, "The Org Manager", "The Org Manager"),
        ("1234", "The Org Manager", "The Org Manager"),
    ],
)
def test_organisation_billing_page_when_the_agreement_is_signed_by_a_known_person(
    organisation_one,
    client_request,
    api_user_active,
    mocker,
    platform_admin_user,
    signed_by_id,
    signed_by_name,
    expected_signatory,
):
    api_user_active["id"] = "1234"

    organisation_one["agreement_signed"] = True
    organisation_one["agreement_signed_version"] = 2.5
    organisation_one["agreement_signed_by_id"] = signed_by_id
    organisation_one["agreement_signed_on_behalf_of_name"] = signed_by_name
    organisation_one["agreement_signed_at"] = "Thu, 20 Feb 2020 00:00:00 GMT"

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    client_request.login(platform_admin_user)
    mocker.patch("app.user_api_client.get_user", return_value=api_user_active)
    page = client_request.get(
        ".organisation_billing",
        org_id=ORGANISATION_ID,
    )

    assert page.select_one("h1").string == "Billing"
    assert "2.5 of the GOV.UK Notify data processing and financial agreement on 20 February 2020" in normalize_spaces(
        page.text
    )
    assert f"{expected_signatory} signed" in page.text
    assert page.select_one("main a")["href"] == url_for(".organisation_download_agreement", org_id=ORGANISATION_ID)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_organisation_billing_page_when_the_agreement_is_signed_by_an_unknown_person(
    organisation_one,
    client_request,
    platform_admin_user,
    mocker,
):
    organisation_one["agreement_signed"] = True
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    client_request.login(platform_admin_user)
    page = client_request.get(
        ".organisation_billing",
        org_id=ORGANISATION_ID,
    )

    assert page.select_one("h1").string == "Billing"
    assert (
        f"{organisation_one['name']} has accepted the GOV.UK Notify data processing and financial agreement."
    ) in page.text
    assert page.select_one("main a")["href"] == url_for(".organisation_download_agreement", org_id=ORGANISATION_ID)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "agreement_signed, expected_content",
    [
        (False, "needs to accept"),
        (None, "has not accepted"),
    ],
)
def test_organisation_billing_page_when_the_agreement_is_not_signed(
    organisation_one,
    client_request,
    platform_admin_user,
    mocker,
    agreement_signed,
    expected_content,
):
    organisation_one["agreement_signed"] = agreement_signed
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    client_request.login(platform_admin_user)
    page = client_request.get(
        ".organisation_billing",
        org_id=ORGANISATION_ID,
    )

    assert page.select_one("h1").string == "Billing"
    assert f"{organisation_one['name']} {expected_content}" in page.text


@pytest.mark.parametrize(
    "crown, expected_status, expected_file_fetched, expected_file_served",
    (
        (
            True,
            200,
            "crown.pdf",
            "GOV.UK Notify data processing and financial agreement.pdf",
        ),
        (
            False,
            200,
            "non-crown.pdf",
            "GOV.UK Notify data processing and financial agreement (non-crown).pdf",
        ),
        (
            None,
            404,
            None,
            None,
        ),
    ),
)
def test_download_organisation_agreement(
    client_request,
    platform_admin_user,
    mocker,
    crown,
    expected_status,
    expected_file_fetched,
    expected_file_served,
):
    mocker.patch(
        "app.models.organisation.organisations_client.get_organisation", return_value=organisation_json(crown=crown)
    )
    mock_get_s3_object = mocker.patch("app.s3_client.s3_mou_client.get_s3_object", return_value=MockS3Object(b"foo"))

    client_request.login(platform_admin_user)
    response = client_request.get_response(
        "main.organisation_download_agreement",
        org_id=ORGANISATION_ID,
        _expected_status=expected_status,
    )

    if expected_file_served:
        assert response.get_data() == b"foo"
        assert response.headers["Content-Type"] == "application/pdf"
        assert response.headers["Content-Disposition"] == (f'attachment; filename="{expected_file_served}"')
        mock_get_s3_object.assert_called_once_with("test-mou", expected_file_fetched)
    else:
        assert not expected_file_fetched
        assert mock_get_s3_object.called is False

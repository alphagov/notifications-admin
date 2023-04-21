from datetime import datetime
from unittest.mock import call

import pytest
from flask import url_for

from app.main.views.providers import add_monthly_traffic


def provider_json(overrides):
    provider = {
        "id": "override-me",
        "active": True,
        "priority": 20,
        "display_name": "Provider",
        "identifier": "override-me",
        "notification_type": "sms",
        "updated_at": None,
        "version": 1,
        "created_by_name": None,
        "supports_international": False,
        "current_month_billable_sms": 0,
    }

    provider.update(**overrides)
    return provider


@pytest.fixture
def sms_provider_1():
    return provider_json(
        {
            "id": "sms_provider_1-id",
            "priority": 20,
            "display_name": "SMS Provider 1",
            "identifier": "sms_provider_1",
            "notification_type": "sms",
            "updated_at": datetime(2017, 1, 16, 15, 20, 40).isoformat(),
            "created_by_name": "Test User",
            "current_month_billable_sms": 5020,
        }
    )


@pytest.fixture
def sms_provider_2():
    return provider_json(
        {
            "id": "sms_provider_2-id",
            "priority": 10,
            "display_name": "SMS Provider 2",
            "identifier": "sms_provider_2",
            "notification_type": "sms",
            "current_month_billable_sms": 6891,
        }
    )


@pytest.fixture
def email_provider_1():
    return provider_json(
        {
            "id": "email_provider_1-id",
            "display_name": "Email Provider 1",
            "identifier": "email_provider_1",
            "notification_type": "email",
        }
    )


@pytest.fixture
def email_provider_2():
    return provider_json(
        {
            "id": "email_provider_2-id",
            "display_name": "Email Provider 2",
            "identifier": "email_provider_2",
            "notification_type": "email",
        }
    )


@pytest.fixture
def sms_provider_intl_1():
    return provider_json(
        {
            "id": "sms_provider_intl_1-id",
            "active": False,
            "display_name": "SMS Provider Intl 1",
            "identifier": "sms_provider_intl_1",
            "notification_type": "sms",
            "supports_international": True,
        }
    )


@pytest.fixture
def sms_provider_intl_2():
    return provider_json(
        {
            "id": "sms_provider_intl_2-id",
            "active": False,
            "display_name": "SMS Provider Intl 2",
            "identifier": "sms_provider_intl_2",
            "notification_type": "sms",
            "supports_international": True,
        }
    )


@pytest.fixture
def stub_providers(
    sms_provider_1,
    sms_provider_2,
    email_provider_1,
    email_provider_2,
    sms_provider_intl_1,
    sms_provider_intl_2,
):
    return {
        "provider_details": [
            sms_provider_1,
            sms_provider_2,
            email_provider_1,
            email_provider_2,
            sms_provider_intl_1,
            sms_provider_intl_2,
        ]
    }


@pytest.fixture
def stub_provider_history():
    return {
        "data": [
            {
                "id": "f9af1ec7-58ef-4f7d-a6f4-5fe7e48644cb",
                "active": True,
                "priority": 20,
                "display_name": "Foo",
                "identifier": "foo",
                "notification_type": "sms",
                "updated_at": None,
                "version": 2,
                "created_by": {
                    "email_address": "test@foo.bar",
                    "name": "Test User",
                    "id": "7cc1dddb-bcbc-4739-8fc1-61bedde3332a",
                },
                "supports_international": False,
            },
            {
                "id": "f9af1ec7-58ef-4f7d-a6f4-5fe7e48644cb",
                "active": True,
                "priority": 10,
                "display_name": "Bar",
                "identifier": "bar",
                "notification_type": "sms",
                "updated_at": None,
                "version": 1,
                "created_by": None,
                "supports_international": False,
            },
        ]
    }


def test_view_providers_shows_all_providers(
    client_request,
    platform_admin_user,
    mocker,
    stub_providers,
):
    mocker.patch(
        "app.provider_client.get_all_providers",
        return_value=stub_providers,
        autospec=True,
    )

    client_request.login(platform_admin_user)
    page = client_request.get("main.view_providers")

    h1 = [header.text.strip() for header in page.select("h1")]

    assert "Providers" in h1

    h2 = [header.text.strip() for header in page.select("h2")]

    assert "Email" in h2
    assert "SMS" in h2

    tables = page.select("table")
    assert len(tables) == 3

    domestic_sms_table = tables[0]
    domestic_email_table = tables[1]
    international_sms_table = tables[2]

    domestic_sms_first_row = domestic_sms_table.select_one("tbody tr")
    table_data = domestic_sms_first_row.select("td")

    assert table_data[0].select_one("a")["href"] == "/provider/sms_provider_1-id"
    assert table_data[0].text.strip() == "SMS Provider 1"
    assert table_data[1].text.strip() == "20"
    assert table_data[2].text.strip() == "42"
    assert table_data[3].text.strip() == "True"
    assert table_data[4].text.strip() == "16 January at 3:20pm"
    assert table_data[5].text.strip() == "Test User"

    domestic_sms_second_row = domestic_sms_table.select_one("tbody").select("tr")[1]
    table_data = domestic_sms_second_row.select("td")

    assert table_data[0].select_one("a")["href"] == "/provider/sms_provider_2-id"
    assert table_data[0].text.strip() == "SMS Provider 2"
    assert table_data[1].text.strip() == "10"
    assert table_data[2].text.strip() == "58"
    assert table_data[3].text.strip() == "True"
    assert table_data[4].text.strip() == "None"
    assert table_data[5].text.strip() == "None"

    domestic_email_first_row = domestic_email_table.select_one("tbody tr")
    domestic_email_table_data = domestic_email_first_row.select("td")

    assert domestic_email_table_data[0].select_one("a")["href"] == "/provider/email_provider_1-id"
    assert domestic_email_table_data[0].text.strip() == "Email Provider 1"
    assert domestic_email_table_data[1].text.strip() == "True"
    assert domestic_email_table_data[2].text.strip() == "None"
    assert domestic_email_table_data[3].text.strip() == "None"

    domestic_email_second_row = domestic_email_table.select_one("tbody").select("tr")[1]
    domestic_email_table_data = domestic_email_second_row.select("td")

    assert domestic_email_table_data[0].select_one("a")["href"] == "/provider/email_provider_2-id"
    assert domestic_email_table_data[0].text.strip() == "Email Provider 2"
    assert domestic_email_table_data[1].text.strip() == "True"
    assert domestic_email_table_data[2].text.strip() == "None"
    assert domestic_email_table_data[3].text.strip() == "None"

    international_sms_first_row = international_sms_table.tbody.select_one("tbody tr")
    table_data = international_sms_first_row.select("td")

    assert table_data[0].select_one("a")["href"] == "/provider/sms_provider_intl_1-id"
    assert table_data[0].text.strip() == "SMS Provider Intl 1"
    assert table_data[1].text.strip() == "False"
    assert table_data[2].text.strip() == "None"
    assert table_data[3].text.strip() == "None"


def test_add_monthly_traffic():
    domestic_sms_providers = [
        {
            "identifier": "mmg",
            "current_month_billable_sms": 27,
        },
        {
            "identifier": "firetext",
            "current_month_billable_sms": 5,
        },
        {
            "identifier": "loadtesting",
            "current_month_billable_sms": 0,
        },
    ]

    add_monthly_traffic(domestic_sms_providers)

    assert domestic_sms_providers == [
        {"identifier": "mmg", "current_month_billable_sms": 27, "monthly_traffic": 84},
        {"identifier": "firetext", "current_month_billable_sms": 5, "monthly_traffic": 16},
        {"identifier": "loadtesting", "current_month_billable_sms": 0, "monthly_traffic": 0},
    ]


def test_view_provider_shows_version_history(client_request, platform_admin_user, mocker, stub_provider_history):
    mocker.patch(
        "app.provider_client.get_provider_versions",
        return_value=stub_provider_history,
        autospec=True,
    )

    client_request.login(platform_admin_user)
    page = client_request.get("main.view_provider", provider_id=stub_provider_history["data"][0]["id"])

    table_rows = page.select("table tr")
    table_headings = table_rows[0].select("th")
    first_row = table_rows[1].select("td")
    second_row = table_rows[2].select("td")

    assert page.select_one("h1").text.strip() == stub_provider_history["data"][0]["display_name"]
    assert len(table_rows) == 3

    assert table_headings[0].text.strip() == "Version"
    assert table_headings[1].text.strip() == "Last Updated"
    assert table_headings[2].text.strip() == "Updated By"
    assert table_headings[3].text.strip() == "Priority"
    assert table_headings[4].text.strip() == "Active"

    assert first_row[0].text.strip() == "2"
    assert first_row[1].text.strip() == "None"
    assert first_row[2].text.strip() == "Test User"
    assert first_row[3].text.strip() == "20"
    assert first_row[4].text.strip() == "True"

    assert second_row[0].text.strip() == "1"
    assert second_row[1].text.strip() == "None"
    assert second_row[2].text.strip() == "None"
    assert second_row[3].text.strip() == "10"
    assert second_row[4].text.strip() == "True"


def test_edit_sms_provider_provider_ratio(client_request, platform_admin_user, mocker, stub_providers, sms_provider_1):
    mocker.patch(
        "app.provider_client.get_all_providers",
        return_value=stub_providers,
        autospec=True,
    )

    client_request.login(platform_admin_user)
    page = client_request.get(
        ".edit_sms_provider_ratio",
    )

    inputs = page.select('.govuk-input[type="text"]')
    assert len(inputs) == 2

    first_input = page.select_one('.govuk-input[name="sms_provider_1"]')
    assert first_input.attrs["value"] == str(sms_provider_1["priority"])


def test_edit_sms_provider_provider_ratio_only_shows_active_providers(
    client_request,
    platform_admin_user,
    mocker,
    stub_providers,
    sms_provider_1,
):
    sms_provider_1["active"] = False

    mocker.patch(
        "app.provider_client.get_all_providers",
        return_value=stub_providers,
    )

    client_request.login(platform_admin_user)
    page = client_request.get(
        ".edit_sms_provider_ratio",
    )

    inputs = page.select('.govuk-input[type="text"]')
    assert len(inputs) == 1


@pytest.mark.parametrize(
    "post_data, expected_calls",
    [
        (
            {"sms_provider_1": 10, "sms_provider_2": 90},
            [
                call("sms_provider_1-id", 10),
                call("sms_provider_2-id", 90),
            ],
        ),
        (
            {"sms_provider_1": 80, "sms_provider_2": 20},
            [
                call("sms_provider_1-id", 80),
                call("sms_provider_2-id", 20),
            ],
        ),
    ],
)
def test_edit_sms_provider_ratio_submit(
    client_request,
    platform_admin_user,
    mocker,
    post_data,
    expected_calls,
    stub_providers,
):
    mocker.patch(
        "app.provider_client.get_all_providers",
        return_value=stub_providers,
        autospec=True,
    )
    mock_update_provider = mocker.patch("app.provider_client.update_provider")

    client_request.login(platform_admin_user)
    client_request.post(
        ".edit_sms_provider_ratio",
        _data=post_data,
        _expected_redirect=url_for(
            ".view_providers",
        ),
    )

    assert mock_update_provider.call_args_list == expected_calls


@pytest.mark.parametrize(
    "post_data, expected_error",
    [
        ({"sms_provider_1": 90, "sms_provider_2": 20}, "Must add up to 100%"),
        ({"sms_provider_1": 101, "sms_provider_2": 20}, "Must be between 0 and 100"),
        ({"sms_provider_1": 99.9, "sms_provider_2": 0.1}, "Percentage must be a whole number"),
    ],
)
def test_edit_sms_provider_submit_invalid_percentages(
    client_request,
    platform_admin_user,
    mocker,
    post_data,
    expected_error,
    stub_providers,
):
    mocker.patch(
        "app.provider_client.get_all_providers",
        return_value=stub_providers,
        autospec=True,
    )
    mock_update_provider = mocker.patch("app.provider_client.update_provider")

    client_request.login(platform_admin_user)
    page = client_request.post(".edit_sms_provider_ratio", _data=post_data, _follow_redirects=True)

    assert expected_error in page.select_one(".govuk-error-message").text
    mock_update_provider.assert_not_called()

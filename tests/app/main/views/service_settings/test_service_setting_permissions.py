import functools

import pytest
from flask import url_for

from app.main.views_nl.service_settings.index import PLATFORM_ADMIN_SERVICE_PERMISSIONS
from tests import organisation_json
from tests.conftest import normalize_spaces


@pytest.fixture
def get_service_settings_page(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_inbound_number_for_service,
    mock_get_all_letter_branding,
    mock_get_organisation,
    mock_get_free_sms_fragment_limit,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    mock_get_service_data_retention,
):
    client_request.login(platform_admin_user)
    return functools.partial(client_request.get, "main.service_settings", service_id=service_one["id"])


def test_service_set_permission_requires_platform_admin(
    client_request,
    service_one,
    mocker,
):
    client_request.post(
        "main.service_set_permission",
        service_id=service_one["id"],
        permission="email_auth",
        _data={"enabled": "True"},
        _expected_status=403,
    )


@pytest.mark.parametrize(
    "initial_permissions, permission, form_data, expected_update",
    [
        (
            [],
            "inbound_sms",
            "True",
            ["inbound_sms"],
        ),
        (
            ["inbound_sms"],
            "inbound_sms",
            "False",
            [],
        ),
        (
            [],
            "email_auth",
            "True",
            ["email_auth"],
        ),
        (
            ["email_auth"],
            "email_auth",
            "False",
            [],
        ),
        (
            [],
            "sms_to_uk_landlines",
            "True",
            ["sms_to_uk_landlines"],
        ),
        (
            ["sms_to_uk_landlines"],
            "sms_to_uk_landlines",
            "False",
            [],
        ),
    ],
)
def test_service_set_permission(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_inbound_number_for_service,
    permission,
    initial_permissions,
    form_data,
    expected_update,
    mocker,
):
    service_one["permissions"] = initial_permissions
    mock_update_service = mocker.patch("app.service_api_client.update_service")
    client_request.login(platform_admin_user)
    client_request.post(
        "main.service_set_permission",
        service_id=service_one["id"],
        permission=permission,
        _data={"enabled": form_data},
        _expected_redirect=url_for(
            "main.service_settings",
            service_id=service_one["id"],
        ),
    )

    assert mock_update_service.call_args[0][0] == service_one["id"]
    new_permissions = mock_update_service.call_args[1]["permissions"]
    assert len(new_permissions) == len(set(new_permissions))
    assert set(new_permissions) == set(expected_update)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "service_fields, endpoint, kwargs, text",
    [
        ({"restricted": True}, ".service_switch_live", {}, "Live Off Change service status"),
        ({"restricted": False}, ".service_switch_live", {}, "Live On Change service status"),
        (
            {"permissions": ["sms"]},
            ".service_set_inbound_number",
            {},
            "Receive inbound SMS Off Change your settings for Receive inbound SMS",
        ),
    ],
)
def test_service_setting_toggles_show(
    notify_admin,
    mock_get_service_organisation,
    get_service_settings_page,
    service_one,
    service_fields,
    endpoint,
    kwargs,
    text,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(agreement_signed=True),
    )
    link_url = url_for(endpoint, **kwargs, service_id=service_one["id"])
    service_one.update(service_fields)
    page = get_service_settings_page()
    assert (
        normalize_spaces(
            page.select_one(f'a[href="{link_url}"]').find_parent("div", class_="govuk-summary-list__row").text.strip()
        )
        == text
    )


@pytest.mark.parametrize(
    "endpoint, index, text", [(".archive_service", 0, "Delete this service"), (".history", 1, "Service history")]
)
@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_service_setting_links_displayed_for_active_services(
    get_service_settings_page,
    service_one,
    endpoint,
    index,
    text,
):
    link_url = url_for(endpoint, service_id=service_one["id"])
    page = get_service_settings_page()
    link = page.select(".page-footer-link a")[index]
    assert normalize_spaces(link.text) == text
    assert link["href"] == link_url


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_service_settings_links_for_archived_service(
    get_service_settings_page,
    service_one,
):
    service_one.update({"active": False})
    page = get_service_settings_page()
    links = page.select("a")

    # There should be a link to the service history page
    assert len([link for link in links if link.get("href") == url_for(".history", service_id=service_one["id"])]) == 1

    # There shouldn't be a link to the archive/delete service page.
    assert (
        len([link for link in links if link.get("href") == url_for(".archive_service", service_id=service_one["id"])])
        == 0
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "permissions,permissions_text,visible",
    [
        ("sms", "inbound SMS", True),
        ("inbound_sms", "inbound SMS", False),  # no sms parent permission
        # also test no permissions set
        ("", "inbound SMS", False),
    ],
)
def test_service_settings_doesnt_show_option_if_parent_permission_disabled(
    get_service_settings_page, service_one, permissions, permissions_text, visible
):
    service_one["permissions"] = [permissions]
    page = get_service_settings_page()
    cells = page.select("dd")
    assert any(cell for cell in cells if permissions_text in cell.text) is visible


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_normal_user_doesnt_see_any_platform_admin_settings(
    client_request,
    service_one,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    mock_get_organisation,
    single_sms_sender,
    mock_get_all_letter_branding,
    mock_get_inbound_number_for_service,
    mock_get_free_sms_fragment_limit,
    mock_get_service_data_retention,
):
    page = client_request.get("main.service_settings", service_id=service_one["id"])
    platform_admin_settings = [permission["title"] for permission in PLATFORM_ADMIN_SERVICE_PERMISSIONS.values()]

    for permission in platform_admin_settings:
        assert permission not in page

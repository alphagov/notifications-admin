import copy
import uuid
from datetime import datetime
from unittest.mock import Mock

import pytest
from flask import url_for
from flask_login import current_user

import app
from app.constants import SERVICE_JOIN_REQUEST_APPROVED, SERVICE_JOIN_REQUEST_REJECTED
from app.formatters import format_date_short
from app.utils.user import is_gov_user
from app.utils.user_permissions import permission_mappings, translate_permissions_from_ui_to_db
from tests import organisation_json
from tests.conftest import (
    ORGANISATION_ID,
    ORGANISATION_TWO_ID,
    SERVICE_ONE_ID,
    USER_ONE_ID,
    create_active_user_empty_permissions,
    create_active_user_manage_template_permissions,
    create_active_user_view_permissions,
    create_active_user_with_permissions,
    create_service_one_user,
    create_user,
    normalize_spaces,
    sample_uuid,
)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "user, expected_self_text, expected_coworker_text",
    [
        (
            create_active_user_with_permissions(),
            (
                "Test User (you) "
                "Can See dashboard "
                "Can Send messages "
                "Can Add and edit templates "
                "Can Manage settings, team and usage "
                "Can Manage API integration"
            ),
            (
                "ZZZZZZZZ zzzzzzz@example.gov.uk "
                "Can See dashboard "
                "Cannot Send messages "
                "Cannot Add and edit templates "
                "Cannot Manage settings, team and usage "
                "Cannot Manage API integration "
                "Change details for ZZZZZZZZ zzzzzzz@example.gov.uk"
            ),
        ),
        (
            create_active_user_empty_permissions(),
            (
                "Test User With Empty Permissions (you) "
                "Cannot See dashboard "
                "Cannot Send messages "
                "Cannot Add and edit templates "
                "Cannot Manage settings, team and usage "
                "Cannot Manage API integration"
            ),
            (
                "ZZZZZZZZ zzzzzzz@example.gov.uk "
                "Can See dashboard "
                "Cannot Send messages "
                "Cannot Add and edit templates "
                "Cannot Manage settings, team and usage "
                "Cannot Manage API integration"
            ),
        ),
        (
            create_active_user_view_permissions(),
            (
                "Test User With Permissions (you) "
                "Can See dashboard "
                "Cannot Send messages "
                "Cannot Add and edit templates "
                "Cannot Manage settings, team and usage "
                "Cannot Manage API integration"
            ),
            (
                "ZZZZZZZZ zzzzzzz@example.gov.uk "
                "Can See dashboard "
                "Cannot Send messages "
                "Cannot Add and edit templates "
                "Cannot Manage settings, team and usage "
                "Cannot Manage API integration"
            ),
        ),
        (
            create_active_user_manage_template_permissions(),
            (
                "Test User With Permissions (you) "
                "Can See dashboard "
                "Cannot Send messages "
                "Can Add and edit templates "
                "Cannot Manage settings, team and usage "
                "Cannot Manage API integration"
            ),
            (
                "ZZZZZZZZ zzzzzzz@example.gov.uk "
                "Can See dashboard "
                "Cannot Send messages "
                "Cannot Add and edit templates "
                "Cannot Manage settings, team and usage "
                "Cannot Manage API integration"
            ),
        ),
        (
            create_active_user_manage_template_permissions(),
            (
                "Test User With Permissions (you) "
                "Can See dashboard "
                "Cannot Send messages "
                "Can Add and edit templates "
                "Cannot Manage settings, team and usage "
                "Cannot Manage API integration"
            ),
            (
                "ZZZZZZZZ zzzzzzz@example.gov.uk "
                "Can See dashboard "
                "Cannot Send messages "
                "Cannot Add and edit templates "
                "Cannot Manage settings, team and usage "
                "Cannot Manage API integration"
            ),
        ),
    ],
)
def test_should_show_overview_page(
    client_request,
    mocker,
    mock_get_invites_for_service,
    mock_get_template_folders,
    service_one,
    user,
    expected_self_text,
    expected_coworker_text,
    active_user_view_permissions,
):
    current_user = user
    other_user = copy.deepcopy(active_user_view_permissions)
    other_user["email_address"] = "zzzzzzz@example.gov.uk"
    other_user["name"] = "ZZZZZZZZ"
    other_user["id"] = "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz"

    mock_get_users = mocker.patch(
        "app.models.user.Users._get_items",
        return_value=[
            current_user,
            other_user,
        ],
    )

    client_request.login(current_user)
    page = client_request.get("main.manage_users", service_id=SERVICE_ONE_ID)

    assert normalize_spaces(page.select_one("h1").text) == "Team members"
    assert normalize_spaces(page.select(".user-list-item")[0].text) == expected_self_text
    # [1:5] are invited users
    assert normalize_spaces(page.select(".user-list-item")[6].text) == expected_coworker_text
    mock_get_users.assert_called_once_with(SERVICE_ONE_ID)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "state",
    (
        "active",
        "pending",
    ),
)
def test_should_show_change_details_link(
    client_request,
    mocker,
    mock_get_invites_for_service,
    mock_get_template_folders,
    service_one,
    active_user_with_permissions,
    active_caseworking_user,
    state,
):
    current_user = active_user_with_permissions

    other_user = active_caseworking_user
    other_user["id"] = uuid.uuid4()
    other_user["email_address"] = "zzzzzzz@example.gov.uk"
    other_user["state"] = state

    mocker.patch("app.user_api_client.get_user", return_value=current_user)
    mocker.patch(
        "app.models.user.Users._get_items",
        return_value=[
            current_user,
            other_user,
        ],
    )

    page = client_request.get("main.manage_users", service_id=SERVICE_ONE_ID)
    link = page.select(".user-list-item")[-1].select_one("a")

    assert normalize_spaces(link.text) == "Change details for Test User zzzzzzz@example.gov.uk"
    assert link["href"] == url_for(
        ".edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=other_user["id"],
    )


@pytest.mark.parametrize(
    "number_of_users",
    (
        pytest.param(7, marks=pytest.mark.xfail),
        pytest.param(8),
    ),
)
def test_should_show_live_search_if_more_than_7_users(
    client_request,
    mocker,
    mock_get_invites_for_service,
    mock_get_template_folders,
    active_user_with_permissions,
    active_user_view_permissions,
    number_of_users,
):
    mocker.patch("app.user_api_client.get_user", return_value=active_user_with_permissions)
    mocker.patch("app.models.user.InvitedUsers._get_items", return_value=[])
    mocker.patch("app.models.user.Users._get_items", return_value=[active_user_with_permissions] * number_of_users)

    page = client_request.get("main.manage_users", service_id=SERVICE_ONE_ID)

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


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_caseworker_on_overview_page(
    client_request,
    mocker,
    mock_get_invites_for_service,
    mock_get_template_folders,
    service_one,
    active_user_view_permissions,
    active_caseworking_user,
):
    service_one["permissions"].append("caseworking")
    current_user = active_user_view_permissions

    other_user = active_caseworking_user
    other_user["id"] = uuid.uuid4()
    other_user["email_address"] = "zzzzzzz@example.gov.uk"

    mocker.patch(
        "app.models.user.Users._get_items",
        return_value=[
            current_user,
            other_user,
        ],
    )

    client_request.login(current_user)
    page = client_request.get("main.manage_users", service_id=SERVICE_ONE_ID)

    assert normalize_spaces(page.select_one("h1").text) == "Team members"
    assert normalize_spaces(page.select(".user-list-item")[0].text) == (
        "Test User With Permissions (you) "
        "Can See dashboard "
        "Cannot Send messages "
        "Cannot Add and edit templates "
        "Cannot Manage settings, team and usage "
        "Cannot Manage API integration"
    )
    # [1:5] are invited users
    assert normalize_spaces(page.select(".user-list-item")[6].text) == (
        "Test User zzzzzzz@example.gov.uk "
        "Cannot See dashboard "
        "Can Send messages "
        "Cannot Add and edit templates "
        "Cannot Manage settings, team and usage "
        "Cannot Manage API integration"
    )


@pytest.mark.parametrize(
    "endpoint, extra_args, service_has_email_auth, auth_options_hidden",
    [
        ("main.edit_user_permissions", {"user_id": sample_uuid()}, True, False),
        ("main.edit_user_permissions", {"user_id": sample_uuid()}, False, True),
        ("main.invite_user", {}, True, False),
        ("main.invite_user", {}, False, True),
    ],
)
def test_service_with_no_email_auth_hides_auth_type_options(
    client_request,
    endpoint,
    extra_args,
    service_has_email_auth,
    auth_options_hidden,
    service_one,
    mock_get_users_by_service,
    mock_get_template_folders,
):
    if service_has_email_auth:
        service_one["permissions"].append("email_auth")
    page = client_request.get(endpoint, service_id=service_one["id"], **extra_args)
    assert (page.select_one("input[name=login_authentication]") is None) == auth_options_hidden


@pytest.mark.parametrize("service_has_caseworking", (True, False))
@pytest.mark.parametrize(
    "endpoint, extra_args",
    [
        (
            "main.edit_user_permissions",
            {"user_id": sample_uuid()},
        ),
        (
            "main.invite_user",
            {},
        ),
    ],
)
def test_service_without_caseworking_doesnt_show_admin_vs_caseworker(
    client_request,
    mock_get_users_by_service,
    mock_get_template_folders,
    endpoint,
    service_has_caseworking,
    extra_args,
):
    page = client_request.get(endpoint, service_id=SERVICE_ONE_ID, **extra_args)
    permission_checkboxes = page.select("input[type=checkbox]")

    for idx in range(len(permission_checkboxes)):
        assert permission_checkboxes[idx]["name"] == "permissions_field"
    assert permission_checkboxes[0]["value"] == "view_activity"
    assert permission_checkboxes[1]["value"] == "send_messages"
    assert permission_checkboxes[2]["value"] == "manage_templates"
    assert permission_checkboxes[3]["value"] == "manage_service"
    assert permission_checkboxes[4]["value"] == "manage_api_keys"


@pytest.mark.parametrize("service_has_email_auth, displays_auth_type", [(True, True), (False, False)])
def test_manage_users_page_shows_member_auth_type_if_service_has_email_auth_activated(
    client_request,
    service_has_email_auth,
    service_one,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_get_template_folders,
    displays_auth_type,
):
    if service_has_email_auth:
        service_one["permissions"].append("email_auth")
    page = client_request.get("main.manage_users", service_id=service_one["id"])
    assert bool(page.select_one(".tick-cross__hint")) == displays_auth_type


def test_manage_users_page_does_not_link_to_user_profile_page_if_not_platform_admins(
    client_request,
    active_user_with_permissions,
    service_one,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_get_template_folders,
):
    active_user_with_permissions["platform_admin"] = False
    client_request.login(active_user_with_permissions)
    page = client_request.get("main.manage_users", service_id=service_one["id"])
    user_links = page.select("h2.user-list-item-heading a")

    assert len(user_links) == 0


def test_manage_users_page_links_to_user_profile_page_for_platform_admins(
    client_request,
    active_user_with_permissions,
    service_one,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_get_template_folders,
):
    active_user_with_permissions["platform_admin"] = True
    client_request.login(active_user_with_permissions)
    page = client_request.get("main.manage_users", service_id=service_one["id"])
    user_links = page.select("h2.user-list-item-heading a")

    assert len(user_links) == 1
    assert user_links[0]["href"] == "/users/6ce466d0-fd6a-11e5-82f5-e0accb9d11a6"


def test_manage_users_page_does_not_links_to_user_profile_page_if_user_only_invited(
    client_request,
    active_user_with_permissions,
    service_one,
    mock_get_invites_for_service,
    mock_get_template_folders,
    mocker,
):
    active_user_with_permissions["platform_admin"] = True
    mocker.patch("app.models.user.Users._get_items", return_value=[])
    client_request.login(active_user_with_permissions)
    page = client_request.get("main.manage_users", service_id=service_one["id"])
    user_links = page.select("h2.user-list-item-heading a")

    assert len(user_links) == 0


@pytest.mark.parametrize(
    "sms_option_disabled, mobile_number, expected_label",
    [
        (
            True,
            None,
            """
            Text message code
            Not available because this team member has not added a phone number to their account
            """,
        ),
        (
            False,
            "07700 900762",
            """
            Text message code
            """,
        ),
    ],
)
def test_user_with_no_mobile_number_cant_be_set_to_sms_auth(
    client_request,
    mock_get_users_by_service,
    mock_get_template_folders,
    sms_option_disabled,
    mobile_number,
    expected_label,
    service_one,
    mocker,
    active_user_with_permissions,
):
    active_user_with_permissions["mobile_number"] = mobile_number

    service_one["permissions"].append("email_auth")
    mocker.patch("app.user_api_client.get_user", return_value=active_user_with_permissions)

    page = client_request.get(
        "main.edit_user_permissions",
        service_id=service_one["id"],
        user_id=sample_uuid(),
    )

    sms_auth_radio_button = page.select_one('input[value="sms_auth"]')
    assert sms_auth_radio_button.has_attr("disabled") == sms_option_disabled
    assert normalize_spaces(page.select_one("label[for=login_authentication-0]").parent.text) == normalize_spaces(
        expected_label
    )


@pytest.mark.parametrize(
    "endpoint, extra_args, expected_checkboxes",
    [
        (
            "main.edit_user_permissions",
            {"user_id": sample_uuid()},
            [
                ("view_activity", True),
                ("send_messages", True),
                ("manage_templates", True),
                ("manage_service", True),
                ("manage_api_keys", True),
            ],
        ),
        (
            "main.invite_user",
            {},
            [
                ("view_activity", False),
                ("send_messages", False),
                ("manage_templates", False),
                ("manage_service", False),
                ("manage_api_keys", False),
            ],
        ),
    ],
)
def test_should_show_page_for_one_user(
    client_request,
    mock_get_users_by_service,
    mock_get_template_folders,
    endpoint,
    extra_args,
    expected_checkboxes,
):
    page = client_request.get(endpoint, service_id=SERVICE_ONE_ID, **extra_args)
    checkboxes = page.select("input[type=checkbox]")

    assert len(checkboxes) == 5

    for index, expected in enumerate(expected_checkboxes):
        expected_input_value, expected_checked = expected
        assert checkboxes[index]["name"] == "permissions_field"
        assert checkboxes[index]["value"] == expected_input_value
        assert checkboxes[index].has_attr("checked") == expected_checked


def test_invite_user_allows_to_choose_auth(
    client_request,
    mock_get_users_by_service,
    mock_get_template_folders,
    service_one,
):
    service_one["permissions"].append("email_auth")
    page = client_request.get("main.invite_user", service_id=SERVICE_ONE_ID)

    radio_buttons = page.select("input[name=login_authentication]")
    values = {button["value"] for button in radio_buttons}

    assert values == {"sms_auth", "email_auth"}
    assert not any(button.has_attr("disabled") for button in radio_buttons)


def test_invite_user_has_correct_email_field(
    client_request,
    mock_get_users_by_service,
    mock_get_template_folders,
):
    email_field = client_request.get("main.invite_user", service_id=SERVICE_ONE_ID).select_one("#email_address")
    assert email_field["spellcheck"] == "false"
    assert "autocomplete" not in email_field


def test_should_not_show_page_for_non_team_member(
    client_request,
    mock_get_users_by_service,
):
    client_request.get(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _expected_status=404,
    )


@pytest.mark.parametrize(
    "submitted_permissions, permissions_sent_to_api",
    [
        (
            {
                "permissions_field": [
                    "view_activity",
                    "send_messages",
                    "manage_templates",
                    "manage_service",
                    "manage_api_keys",
                ]
            },
            {
                "view_activity",
                "send_messages",
                "manage_service",
                "manage_templates",
                "manage_api_keys",
            },
        ),
        (
            {
                "permissions_field": [
                    "view_activity",
                    "send_messages",
                    "manage_templates",
                ]
            },
            {
                "view_activity",
                "send_messages",
                "manage_templates",
            },
        ),
        (
            {},
            set(),
        ),
    ],
)
def test_edit_user_permissions(
    client_request,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    mock_get_template_folders,
    fake_uuid,
    submitted_permissions,
    permissions_sent_to_api,
):
    client_request.post(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
        _data=dict(email_address="test@example.com", **submitted_permissions),
        _expected_status=302,
        _expected_redirect=url_for(
            "main.manage_users",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_set_user_permissions.assert_called_with(
        fake_uuid, SERVICE_ONE_ID, permissions=permissions_sent_to_api, folder_permissions=[]
    )


def test_edit_user_folder_permissions(
    client_request,
    service_one,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    mock_get_template_folders,
    fake_uuid,
):
    mock_get_template_folders.return_value = [
        {"id": "folder-id-1", "name": "folder_one", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-2", "name": "folder_one", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-3", "name": "folder_one", "parent_id": "folder-id-1", "users_with_permission": []},
    ]

    page = client_request.get(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
    )
    assert [item["value"] for item in page.select("input[name=folder_permissions]")] == [
        "folder-id-1",
        "folder-id-3",
        "folder-id-2",
    ]

    client_request.post(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
        _data={"folder_permissions": ["folder-id-1", "folder-id-3"]},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.manage_users",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_set_user_permissions.assert_called_with(
        fake_uuid, SERVICE_ONE_ID, permissions=set(), folder_permissions=["folder-id-1", "folder-id-3"]
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_cant_edit_user_folder_permissions_for_platform_admin_users(
    client_request,
    mocker,
    service_one,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    mock_get_template_folders,
    platform_admin_user,
):
    service_one["permissions"] = ["edit_folder_permissions"]
    mocker.patch("app.user_api_client.get_user", return_value=platform_admin_user)
    mock_get_template_folders.return_value = [
        {"id": "folder-id-1", "name": "folder_one", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-2", "name": "folder_one", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-3", "name": "folder_one", "parent_id": "folder-id-1", "users_with_permission": []},
    ]
    page = client_request.get(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=platform_admin_user["id"],
    )
    assert normalize_spaces(page.select("main p")[0].text) == "platform@admin.gov.uk Change email address"
    assert normalize_spaces(page.select("main p")[2].text) == "Platform admin users can access all template folders."
    assert page.select("input[name=folder_permissions]") == []
    client_request.post(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=platform_admin_user["id"],
        _data={},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.manage_users",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_set_user_permissions.assert_called_with(
        platform_admin_user["id"],
        SERVICE_ONE_ID,
        permissions={
            "manage_api_keys",
            "manage_service",
            "manage_templates",
            "send_messages",
            "view_activity",
        },
        folder_permissions=None,
    )


def test_cant_edit_non_member_user_permissions(
    client_request,
    mock_get_users_by_service,
    mock_set_user_permissions,
):
    client_request.post(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _data={
            "email_address": "test@example.com",
            "manage_service": "y",
        },
        _expected_status=404,
    )
    assert mock_set_user_permissions.called is False


def test_edit_user_permissions_including_authentication_with_email_auth_service(
    client_request,
    service_one,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    mock_update_user_attribute,
    mock_get_template_folders,
):
    active_user_with_permissions["auth_type"] = "email_auth"
    service_one["permissions"].append("email_auth")

    client_request.post(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _data={
            "email_address": active_user_with_permissions["email_address"],
            "permissions_field": [
                "send_messages",
                "manage_templates",
                "manage_service",
                "manage_api_keys",
            ],
            "login_authentication": "sms_auth",
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.manage_users",
            service_id=SERVICE_ONE_ID,
        ),
    )

    mock_set_user_permissions.assert_called_with(
        str(active_user_with_permissions["id"]),
        SERVICE_ONE_ID,
        permissions={
            "send_messages",
            "manage_templates",
            "manage_service",
            "manage_api_keys",
        },
        folder_permissions=[],
    )
    mock_update_user_attribute.assert_called_with(str(active_user_with_permissions["id"]), auth_type="sms_auth")


def test_edit_user_permissions_shows_authentication_for_email_auth_service(
    client_request,
    service_one,
    mock_get_users_by_service,
    mock_get_template_folders,
    active_user_with_permissions,
):
    service_one["permissions"].append("email_auth")

    page = client_request.get(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
    )

    radio_buttons = page.select("input[name=login_authentication]")
    values = {button["value"] for button in radio_buttons}

    assert values == {"sms_auth", "email_auth"}
    assert not any(button.has_attr("disabled") for button in radio_buttons)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_edit_user_permissions_hides_authentication_for_webauthn_user(
    client_request,
    service_one,
    mock_get_users_by_service,
    mock_get_template_folders,
    active_user_with_permissions,
):
    active_user_with_permissions["auth_type"] = "webauthn_auth"
    service_one["permissions"].append("email_auth")

    page = client_request.get(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
    )

    assert "This user will login with a security key" in str(page)
    assert page.select_one("#login_authentication") is None


@pytest.mark.parametrize("new_auth_type", ["sms_auth", "email_auth"])
def test_edit_user_permissions_preserves_auth_type_for_webauthn_user(
    client_request,
    service_one,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    mock_update_user_attribute,
    mock_get_template_folders,
    new_auth_type,
):
    active_user_with_permissions["auth_type"] = "webauthn_auth"
    service_one["permissions"].append("email_auth")

    client_request.post(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _data={
            "email_address": active_user_with_permissions["email_address"],
            "permissions_field": [],
            "login_authentication": new_auth_type,
        },
        _expected_status=302,
    )

    mock_set_user_permissions.assert_called_with(
        str(active_user_with_permissions["id"]),
        SERVICE_ONE_ID,
        permissions=set(),
        folder_permissions=[],
    )
    mock_update_user_attribute.assert_not_called()


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_page_for_inviting_user(
    client_request,
    mock_get_template_folders,
):
    page = client_request.get(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
    )

    assert "Invite a team member" in page.select_one("h1").text.strip()
    assert not page.select_one("div.checkboxes-nested")


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_page_for_inviting_user_with_email_prefilled(
    client_request,
    mocker,
    service_one,
    mock_get_template_folders,
    fake_uuid,
    active_user_with_permissions,
    active_user_with_permission_to_other_service,
    mock_get_organisation_by_domain,
    mock_get_invites_for_service,
):
    service_one["organisation"] = ORGANISATION_ID

    client_request.login(active_user_with_permissions)
    mocker.patch(
        "app.user_api_client.get_user",
        return_value=active_user_with_permission_to_other_service,
    )
    page = client_request.get(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
        # We have the user’s name in the H1 but don’t want it duplicated
        # in the page title
        _test_page_title=False,
    )
    assert normalize_spaces(page.select_one("title").text).startswith("Let someone join your service")
    assert normalize_spaces(page.select_one("h1").text) == "Let Service Two User join your service"
    assert normalize_spaces(page.select_one("main .govuk-body").text) == "service-two-user@test.gov.uk"
    assert not page.select("input#email_address") or page.select("input[type=email]")


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_page_if_prefilled_user_is_already_a_team_member(
    client_request,
    mock_get_template_folders,
    fake_uuid,
    active_user_with_permissions,
    active_caseworking_user,
    mocker,
):
    mocker.patch(
        "app.models.user.user_api_client.get_user",
        side_effect=[
            # First call is to get the current user
            active_user_with_permissions,
            # Second call gets the user to invite
            active_caseworking_user,
        ],
    )
    page = client_request.get(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
    )

    assert normalize_spaces(page.select_one("title").text).startswith("This person is already a team member")
    assert normalize_spaces(page.select_one("h1").text) == "This person is already a team member"
    assert normalize_spaces(page.select_one("main .govuk-body").text) == (
        "Test User is already member of ‘service one’."
    )
    assert not page.select("form")


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_page_if_prefilled_user_is_already_invited(
    client_request,
    mock_get_template_folders,
    fake_uuid,
    active_user_with_permissions,
    active_user_with_permission_to_other_service,
    mock_get_invites_for_service,
    mocker,
):
    active_user_with_permission_to_other_service["email_address"] = "user_1@testnotify.gov.uk"
    client_request.login(active_user_with_permissions)
    mocker.patch(
        "app.models.user.user_api_client.get_user",
        return_value=active_user_with_permission_to_other_service,
    )
    page = client_request.get(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
    )

    assert normalize_spaces(page.select_one("title").text).startswith("This person has already received an invite")
    assert normalize_spaces(page.select_one("h1").text) == "This person has already received an invite"
    assert normalize_spaces(page.select_one("main .govuk-body").text) == (
        "Service Two User has not accepted their invitation to ‘service one’ yet. You do not need to do anything."
    )
    assert not page.select("form")


def test_should_403_if_trying_to_prefill_email_address_for_user_with_no_organisation(
    client_request,
    service_one,
    mock_get_template_folders,
    fake_uuid,
    active_user_with_permissions,
    active_user_with_permission_to_other_service,
    mock_get_invites_for_service,
    mock_get_no_organisation_by_domain,
    mocker,
):
    service_one["organisation"] = ORGANISATION_ID
    client_request.login(active_user_with_permissions)
    mocker.patch(
        "app.models.user.user_api_client.get_user",
        return_value=active_user_with_permission_to_other_service,
    )
    client_request.get(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
        _expected_status=403,
    )


def test_should_403_if_trying_to_prefill_email_address_for_user_from_other_organisation(
    client_request,
    service_one,
    mock_get_template_folders,
    fake_uuid,
    active_user_with_permissions,
    active_user_with_permission_to_other_service,
    mock_get_invites_for_service,
    mock_get_organisation_by_domain,
    mocker,
):
    service_one["organisation"] = ORGANISATION_TWO_ID
    client_request.login(active_user_with_permissions)
    mocker.patch(
        "app.models.user.user_api_client.get_user",
        return_value=active_user_with_permission_to_other_service,
    )
    client_request.get(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
        _expected_status=403,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_folder_permission_form_if_service_has_folder_permissions_enabled(
    client_request, mock_get_template_folders, service_one
):
    mock_get_template_folders.return_value = [
        {"id": "folder-id-1", "name": "folder_one", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-2", "name": "folder_two", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-3", "name": "folder_three", "parent_id": "folder-id-1", "users_with_permission": []},
    ]
    page = client_request.get(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
    )

    assert "Invite a team member" in page.select_one("h1").text.strip()

    folder_checkboxes = page.select_one("div.selection-wrapper").select("li")
    assert len(folder_checkboxes) == 3


@pytest.mark.parametrize("email_address, gov_user", [("test@example.gov.uk", True), ("test@example.com", False)])
@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_invite_user(
    client_request,
    active_user_with_permissions,
    mocker,
    sample_invite,
    email_address,
    gov_user,
    mock_get_template_folders,
    mock_get_organisations,
):
    sample_invite["email_address"] = email_address

    assert is_gov_user(email_address) == gov_user
    mocker.patch("app.models.user.InvitedUsers._get_items", return_value=[sample_invite])
    mocker.patch("app.models.user.Users._get_items", return_value=[active_user_with_permissions])
    mocker.patch("app.invite_api_client.create_invite", return_value=sample_invite)
    page = client_request.post(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        _data={
            "email_address": email_address,
            "permissions_field": [
                "view_activity",
                "send_messages",
                "manage_templates",
                "manage_service",
                "manage_api_keys",
            ],
        },
        _follow_redirects=True,
    )
    assert page.select_one("h1").string.strip() == "Team members"
    flash_banner = page.select_one("div.banner-default-with-tick").get_text().strip()
    assert flash_banner == f"Invite sent to {email_address}"

    expected_permissions = {"manage_api_keys", "manage_service", "manage_templates", "send_messages", "view_activity"}

    app.invite_api_client.create_invite.assert_called_once_with(
        sample_invite["from_user"], sample_invite["service"], email_address, expected_permissions, "sms_auth", []
    )


def test_invite_user_when_email_address_is_prefilled(
    client_request,
    service_one,
    active_user_with_permissions,
    active_user_with_permission_to_other_service,
    fake_uuid,
    mocker,
    sample_invite,
    mock_get_template_folders,
    mock_get_invites_for_service,
    mock_get_organisation_by_domain,
):
    service_one["organisation"] = ORGANISATION_ID
    client_request.login(active_user_with_permissions)
    mocker.patch(
        "app.models.user.user_api_client.get_user",
        return_value=active_user_with_permission_to_other_service,
    )
    mocker.patch("app.invite_api_client.create_invite", return_value=sample_invite)
    client_request.post(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
        _data={
            # No posted email address
            "permissions_field": [
                "send_messages",
            ],
        },
    )

    app.invite_api_client.create_invite.assert_called_once_with(
        active_user_with_permissions["id"],
        SERVICE_ONE_ID,
        active_user_with_permission_to_other_service["email_address"],
        {"send_messages"},
        "sms_auth",
        [],
    )


@pytest.mark.parametrize("auth_type", [("sms_auth"), "email_auth"])
@pytest.mark.parametrize("email_address, gov_user", [("test@example.gov.uk", True), ("test@example.com", False)])
@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_invite_user_with_email_auth_service(
    client_request,
    service_one,
    active_user_with_permissions,
    sample_invite,
    email_address,
    gov_user,
    mocker,
    auth_type,
    mock_get_organisations,
    mock_get_template_folders,
):
    service_one["permissions"].append("email_auth")
    sample_invite["email_address"] = "test@example.gov.uk"

    assert is_gov_user(email_address) is gov_user
    mocker.patch("app.models.user.InvitedUsers._get_items", return_value=[sample_invite])
    mocker.patch("app.models.user.Users._get_items", return_value=[active_user_with_permissions])
    mocker.patch("app.invite_api_client.create_invite", return_value=sample_invite)

    page = client_request.post(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        _data={
            "email_address": email_address,
            "permissions_field": [
                "view_activity",
                "send_messages",
                "manage_templates",
                "manage_service",
                "manage_api_keys",
            ],
            "login_authentication": auth_type,
        },
        _follow_redirects=True,
        _expected_status=200,
    )

    assert page.select_one("h1").string.strip() == "Team members"
    flash_banner = page.select_one("div.banner-default-with-tick").get_text().strip()
    assert flash_banner == "Invite sent to test@example.gov.uk"

    expected_permissions = {"manage_api_keys", "manage_service", "manage_templates", "send_messages", "view_activity"}

    app.invite_api_client.create_invite.assert_called_once_with(
        sample_invite["from_user"], sample_invite["service"], email_address, expected_permissions, auth_type, []
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_cancel_invited_user_cancels_user_invitations(
    client_request,
    mock_get_invites_for_service,
    sample_invite,
    mock_get_users_by_service,
    mock_get_template_folders,
    mocker,
):
    mock_cancel = mocker.patch("app.invite_api_client.cancel_invited_user")
    mocker.patch("app.invite_api_client.get_invited_user_for_service", return_value=sample_invite)

    page = client_request.get(
        "main.cancel_invited_user",
        service_id=SERVICE_ONE_ID,
        invited_user_id=sample_invite["id"],
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Team members"
    flash_banner = normalize_spaces(page.select_one("div.banner-default-with-tick").text)
    assert flash_banner == f"Invitation cancelled for {sample_invite['email_address']}"
    mock_cancel.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        invited_user_id=sample_invite["id"],
    )


def test_cancel_invited_user_doesnt_work_if_user_not_invited_to_this_service(
    client_request,
    mock_get_invites_for_service,
    mocker,
):
    mock_cancel = mocker.patch("app.invite_api_client.cancel_invited_user")
    client_request.get(
        "main.cancel_invited_user",
        service_id=SERVICE_ONE_ID,
        invited_user_id=sample_uuid(),
        _expected_status=404,
    )
    assert mock_cancel.called is False


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "invite_status, expected_text",
    [
        (
            "pending",
            (
                "invited_user@test.gov.uk (invited) "
                "Can See dashboard "
                "Can Send messages "
                "Cannot Add and edit templates "
                "Can Manage settings, team and usage "
                "Can Manage API integration "
                "Cancel invitation for invited_user@test.gov.uk"
            ),
        ),
        (
            "cancelled",
            (
                "invited_user@test.gov.uk (cancelled invite) "
                # all permissions are greyed out
                "Cannot See dashboard "
                "Cannot Send messages "
                "Cannot Add and edit templates "
                "Cannot Manage settings, team and usage "
                "Cannot Manage API integration"
            ),
        ),
    ],
)
def test_manage_users_shows_invited_user(
    client_request,
    mocker,
    active_user_with_permissions,
    mock_get_template_folders,
    sample_invite,
    invite_status,
    expected_text,
):
    sample_invite["status"] = invite_status
    mocker.patch("app.models.user.InvitedUsers._get_items", return_value=[sample_invite])
    mocker.patch("app.models.user.Users._get_items", return_value=[active_user_with_permissions])

    page = client_request.get("main.manage_users", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").string.strip() == "Team members"
    assert normalize_spaces(page.select(".user-list-item")[0].text) == expected_text


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_manage_users_does_not_show_accepted_invite(
    client_request,
    mocker,
    active_user_with_permissions,
    sample_invite,
    mock_get_template_folders,
):
    invited_user_id = uuid.uuid4()
    sample_invite["id"] = invited_user_id
    sample_invite["status"] = "accepted"
    mocker.patch("app.models.user.InvitedUsers._get_items", return_value=[sample_invite])
    mocker.patch("app.models.user.Users._get_items", return_value=[active_user_with_permissions])

    page = client_request.get("main.manage_users", service_id=SERVICE_ONE_ID)

    assert page.select_one("h1").string.strip() == "Team members"
    user_lists = page.select("div.user-list")
    assert len(user_lists) == 1
    assert "invited_user@test.gov.uk" not in page.text


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_user_cant_invite_themselves(
    client_request,
    active_user_with_permissions,
    mock_create_invite,
    mock_get_template_folders,
):
    page = client_request.post(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        _data={
            "email_address": active_user_with_permissions["email_address"],
            "permissions_field": ["send_messages", "manage_service", "manage_api_keys"],
        },
        _follow_redirects=True,
        _expected_status=200,
    )
    assert page.select_one("h1").string.strip() == "Invite a team member"
    form_error = page.select_one(".govuk-error-message").text.strip()
    assert form_error == "Error: Enter an email address that is not your own"
    assert not mock_create_invite.called


def test_no_permission_manage_users_page(
    client_request,
    service_one,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_get_template_folders,
):
    resp_text = client_request.get("main.manage_users", service_id=service_one["id"])
    assert url_for(".invite_user", service_id=service_one["id"]) not in resp_text
    assert "Edit permission" not in resp_text
    assert "Team members" not in resp_text


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "folders_user_can_see, expected_message",
    [
        (3, "Can see all folders"),
        (2, "Can see 2 folders"),
        (1, "Can see 1 folder"),
        (0, "Cannot see any folders"),
    ],
)
def test_manage_user_page_shows_how_many_folders_user_can_view(
    client_request,
    service_one,
    mock_get_template_folders,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    api_user_active,
    folders_user_can_see,
    expected_message,
):
    service_one["permissions"] = ["edit_folder_permissions"]
    mock_get_template_folders.return_value = [
        {"id": "folder-id-1", "name": "f1", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-2", "name": "f2", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-3", "name": "f3", "parent_id": None, "users_with_permission": []},
    ]
    for i in range(folders_user_can_see):
        mock_get_template_folders.return_value[i]["users_with_permission"].append(api_user_active["id"])

    page = client_request.get("main.manage_users", service_id=service_one["id"])

    user_div = page.select_one("h2[title='notify@digital.cabinet-office.gov.uk']").parent
    assert user_div.select_one(".tick-cross__hint:last-child").text.strip() == expected_message


def test_manage_user_page_doesnt_show_folder_hint_if_service_has_no_folders(
    client_request,
    service_one,
    mock_get_template_folders,
    mock_get_users_by_service,
    mock_get_invites_for_service,
):
    service_one["permissions"] = ["edit_folder_permissions"]
    mock_get_template_folders.return_value = []

    page = client_request.get("main.manage_users", service_id=service_one["id"])

    user_div = page.select_one("h2[title='notify@digital.cabinet-office.gov.uk']").parent
    assert user_div.find(".tick-cross__hint:last-child") is None


def test_manage_user_page_doesnt_show_folder_hint_if_service_cant_edit_folder_permissions(
    client_request,
    service_one,
    mock_get_template_folders,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    api_user_active,
):
    service_one["permissions"] = []
    mock_get_template_folders.return_value = [
        {"id": "folder-id-1", "name": "f1", "parent_id": None, "users_with_permission": [api_user_active["id"]]},
    ]

    page = client_request.get("main.manage_users", service_id=service_one["id"])

    user_div = page.select_one("h2[title='notify@digital.cabinet-office.gov.uk']").parent
    assert user_div.find(".tick-cross__hint:last-child") is None


def test_remove_user_from_service(
    client_request, active_user_with_permissions, api_user_active, service_one, mock_remove_user_from_service, mocker
):
    mock_event_handler = mocker.patch("app.main.views_nl.manage_users.Events.remove_user_from_service")

    client_request.post(
        "main.remove_user_from_service",
        service_id=service_one["id"],
        user_id=active_user_with_permissions["id"],
        _expected_redirect=url_for("main.manage_users", service_id=service_one["id"]),
    )
    mock_remove_user_from_service.assert_called_once_with(service_one["id"], str(active_user_with_permissions["id"]))

    mock_event_handler.assert_called_once_with(
        user_id=active_user_with_permissions["id"],
        removed_by_id=api_user_active["id"],
        service_id=service_one["id"],
    )


def test_can_invite_user_as_platform_admin(
    client_request,
    service_one,
    platform_admin_user,
    active_user_with_permissions,
    mock_get_invites_for_service,
    mock_get_template_folders,
    mocker,
):
    mocker.patch("app.models.user.Users._get_items", return_value=[active_user_with_permissions])

    client_request.login(platform_admin_user)

    page = client_request.get(
        "main.manage_users",
        service_id=SERVICE_ONE_ID,
    )
    assert url_for(".invite_user", service_id=service_one["id"]) in str(page)


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_edit_user_email_page(
    client_request, active_user_with_permissions, service_one, mock_get_users_by_service, mocker
):
    user = active_user_with_permissions
    mocker.patch("app.user_api_client.get_user", return_value=user)

    page = client_request.get("main.edit_user_email", service_id=service_one["id"], user_id=sample_uuid())

    assert page.select_one("h1").text == "Change team member’s email address"
    assert page.select("p[id=user_name]")[0].text == f"This will change the email address for {user['name']}."
    assert page.select("input[type=email]")[0].attrs["value"] == user["email_address"]
    assert normalize_spaces(page.select("form button")[0].text) == "Save"


def test_edit_user_email_page_404_for_non_team_member(
    client_request,
    mock_get_users_by_service,
):
    client_request.get(
        "main.edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _expected_status=404,
    )


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_edit_user_email_redirects_to_confirmation(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_get_user_by_email_not_found,
):
    client_request.post(
        "main.edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _expected_status=302,
        _expected_redirect=url_for(
            "main.confirm_edit_user_email",
            service_id=SERVICE_ONE_ID,
            user_id=active_user_with_permissions["id"],
        ),
    )
    with client_request.session_transaction() as session:
        assert session[f"team_member_email_change-{active_user_with_permissions['id']}"] == "test@user.gov.uk"


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_edit_user_email_without_changing_goes_back_to_team_members(
    client_request,
    active_user_with_permissions,
    mock_get_user_by_email,
    mock_get_users_by_service,
    mock_update_user_attribute,
):
    client_request.post(
        "main.edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _data={"email_address": active_user_with_permissions["email_address"]},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.manage_users",
            service_id=SERVICE_ONE_ID,
        ),
    )
    assert mock_update_user_attribute.called is False


@pytest.mark.parametrize("original_email_address", ["test@gov.uk", "test@example.com"])
def test_edit_user_email_can_change_any_email_address_to_a_gov_email_address(
    client_request,
    active_user_with_permissions,
    mock_get_user_by_email_not_found,
    mock_get_users_by_service,
    mock_get_organisations,
    original_email_address,
):
    active_user_with_permissions["email_address"] = original_email_address

    client_request.post(
        "main.edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _data={"email_address": "new-email-address@gov.uk"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.confirm_edit_user_email",
            service_id=SERVICE_ONE_ID,
            user_id=active_user_with_permissions["id"],
        ),
    )


def test_edit_user_email_can_change_a_non_gov_email_address_to_another_non_gov_email_address(
    client_request,
    active_user_with_permissions,
    mock_get_user_by_email_not_found,
    mock_get_users_by_service,
    mock_get_organisations,
):
    active_user_with_permissions["email_address"] = "old@example.com"

    client_request.post(
        "main.edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _data={"email_address": "new@example.com"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.confirm_edit_user_email",
            service_id=SERVICE_ONE_ID,
            user_id=active_user_with_permissions["id"],
        ),
    )


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_edit_user_email_cannot_change_a_gov_email_address_to_a_non_gov_email_address(
    client_request,
    active_user_with_permissions,
    mock_get_user_by_email_not_found,
    mock_get_users_by_service,
    mock_get_organisations,
):
    page = client_request.post(
        "main.edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _data={"email_address": "new_email@example.com"},
        _expected_status=200,
    )
    assert "Enter a public sector email address" in page.select_one(".govuk-error-message").text
    with client_request.session_transaction() as session:
        assert f"team_member_email_change-{active_user_with_permissions['id']}" not in session


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_confirm_edit_user_email_page(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_get_user,
):
    new_email = "new_email@gov.uk"
    with client_request.session_transaction() as session:
        session[f"team_member_email_change-{active_user_with_permissions['id']}"] = new_email

    page = client_request.get(
        "main.confirm_edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
    )

    assert "Confirm change of email address" in page.text
    for text in [
        "New email address:",
        new_email,
        f"We will send {active_user_with_permissions['name']} an email to tell them about the change.",
    ]:
        assert text in page.text
    assert "Confirm" in page.text


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_confirm_edit_user_email_page_redirects_if_session_empty(
    client_request,
    mock_get_users_by_service,
    active_user_with_permissions,
):
    page = client_request.get(
        "main.confirm_edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _follow_redirects=True,
    )
    assert "Confirm change of email address" not in page.text


def test_confirm_edit_user_email_page_404s_for_non_team_member(
    client_request,
    mock_get_users_by_service,
):
    client_request.get(
        "main.confirm_edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _expected_status=404,
    )


def test_confirm_edit_user_email_changes_user_email(
    client_request,
    active_user_with_permissions,
    api_user_active,
    service_one,
    mocker,
    mock_update_user_attribute,
):
    # We want active_user_with_permissions (the current user) to update the email address for api_user_active
    # By default both users would have the same id, so we change the id of api_user_active
    api_user_active["id"] = str(uuid.uuid4())
    mocker.patch("app.models.user.Users._get_items", return_value=[api_user_active, active_user_with_permissions])
    # get_user gets called twice - first to check if current user can see the page, then to see if the team member
    # whose email address we're changing belongs to the service
    mocker.patch("app.user_api_client.get_user", side_effect=[active_user_with_permissions, api_user_active])
    mock_event_handler = mocker.patch("app.main.views_nl.manage_users.Events.update_user_email")

    new_email = "new_email@gov.uk"
    with client_request.session_transaction() as session:
        session[f"team_member_email_change-{api_user_active['id']}"] = new_email

    client_request.post(
        "main.confirm_edit_user_email",
        service_id=service_one["id"],
        user_id=api_user_active["id"],
        _expected_status=302,
        _expected_redirect=url_for(
            "main.manage_users",
            service_id=SERVICE_ONE_ID,
        ),
    )

    mock_update_user_attribute.assert_called_once_with(
        api_user_active["id"], email_address=new_email, updated_by=active_user_with_permissions["id"]
    )
    mock_event_handler.assert_called_once_with(
        user_id=api_user_active["id"],
        updated_by_id=active_user_with_permissions["id"],
        original_email_address=api_user_active["email_address"],
        new_email_address=new_email,
    )


def test_confirm_edit_user_email_doesnt_change_user_email_for_non_team_member(
    client_request,
    mock_get_users_by_service,
):
    with client_request.session_transaction() as session:
        session["team_member_email_change"] = "new_email@gov.uk"
    client_request.post(
        "main.confirm_edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _expected_status=404,
    )


def test_edit_user_permissions_page_displays_redacted_mobile_number_and_change_link(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_get_template_folders,
    service_one,
):
    page = client_request.get(
        "main.edit_user_permissions",
        service_id=service_one["id"],
        user_id=active_user_with_permissions["id"],
    )

    assert active_user_with_permissions["name"] in page.select_one("h1").text
    mobile_number_paragraph = page.select("p[id=user_mobile_number]")[0]
    assert "0770 •  •  •  • 762" in mobile_number_paragraph.text
    change_link = mobile_number_paragraph.findChild()
    assert change_link.attrs["href"] == "/services/{}/users/{}/edit-mobile-number".format(
        service_one["id"], active_user_with_permissions["id"]
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_edit_user_permissions_with_delete_query_shows_banner(
    client_request, active_user_with_permissions, mock_get_users_by_service, mock_get_template_folders, service_one
):
    page = client_request.get(
        "main.edit_user_permissions", service_id=service_one["id"], user_id=active_user_with_permissions["id"], delete=1
    )

    banner = page.select_one("div.banner-dangerous")
    assert banner.contents[0].strip() == "Are you sure you want to remove Test User?"
    assert banner.form.attrs["action"] == url_for(
        "main.remove_user_from_service", service_id=service_one["id"], user_id=active_user_with_permissions["id"]
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_edit_user_mobile_number_page(
    client_request, active_user_with_permissions, mock_get_users_by_service, service_one
):
    page = client_request.get(
        "main.edit_user_mobile_number",
        service_id=service_one["id"],
        user_id=active_user_with_permissions["id"],
    )

    assert page.select_one("h1").text == "Change team member’s mobile number"
    assert page.select("p[id=user_name]")[0].text == "This will change the mobile number for {}.".format(
        active_user_with_permissions["name"]
    )
    assert page.select("input[name=mobile_number]")[0].attrs["value"] == "0770••••762"
    assert normalize_spaces(page.select("form button")[0].text) == "Save"


@pytest.mark.skip(reason="[NOTIFYNL] Dutch phone number implementation breaks this test")
def test_edit_user_mobile_number_redirects_to_confirmation(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
):
    client_request.post(
        "main.edit_user_mobile_number",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _data={"mobile_number": "07554080636"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.confirm_edit_user_mobile_number",
            service_id=SERVICE_ONE_ID,
            user_id=active_user_with_permissions["id"],
        ),
    )


def test_edit_user_mobile_number_redirects_to_manage_users_if_number_not_changed(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    service_one,
):
    client_request.post(
        "main.edit_user_mobile_number",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _data={"mobile_number": "0770••••762"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.manage_users",
            service_id=SERVICE_ONE_ID,
        ),
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_confirm_edit_user_mobile_number_page(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    service_one,
):
    new_number = "07554080636"
    with client_request.session_transaction() as session:
        session["team_member_mobile_change"] = new_number
    page = client_request.get(
        "main.confirm_edit_user_mobile_number",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
    )

    assert "Confirm change of mobile number" in page.text
    for text in [
        "New mobile number:",
        new_number,
        f"We will send {active_user_with_permissions['name']} a text message to tell them about the change.",
    ]:
        assert text in page.text
    assert "Confirm" in page.text


def test_confirm_edit_user_mobile_number_page_redirects_if_session_empty(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    service_one,
):
    page = client_request.get(
        "main.confirm_edit_user_mobile_number",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _expected_redirect=url_for(
            "main.edit_user_mobile_number",
            service_id=SERVICE_ONE_ID,
            user_id=active_user_with_permissions["id"],
        ),
    )
    assert "Confirm change of mobile number" not in page.text


def test_confirm_edit_user_mobile_number_changes_user_mobile_number(
    client_request, active_user_with_permissions, api_user_active, service_one, mocker, mock_update_user_attribute
):
    # We want active_user_with_permissions (the current user) to update the mobile number for api_user_active
    # By default both users would have the same id, so we change the id of api_user_active
    api_user_active["id"] = str(uuid.uuid4())

    mocker.patch("app.models.user.Users._get_items", return_value=[api_user_active, active_user_with_permissions])
    # get_user gets called twice - first to check if current user can see the page, then to see if the team member
    # whose mobile number we're changing belongs to the service
    mocker.patch("app.user_api_client.get_user", side_effect=[active_user_with_permissions, api_user_active])
    mock_event_handler = mocker.patch("app.main.views_nl.manage_users.Events.update_user_mobile_number")

    new_number = "07554080636"
    with client_request.session_transaction() as session:
        session["team_member_mobile_change"] = new_number

    client_request.post(
        "main.confirm_edit_user_mobile_number",
        service_id=SERVICE_ONE_ID,
        user_id=api_user_active["id"],
        _expected_status=302,
        _expected_redirect=url_for(
            "main.manage_users",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_update_user_attribute.assert_called_once_with(
        api_user_active["id"], mobile_number=new_number, updated_by=active_user_with_permissions["id"]
    )
    mock_event_handler.assert_called_once_with(
        user_id=api_user_active["id"],
        updated_by_id=active_user_with_permissions["id"],
        original_mobile_number=api_user_active["mobile_number"],
        new_mobile_number=new_number,
    )


def test_confirm_edit_user_mobile_number_doesnt_change_user_mobile_for_non_team_member(
    client_request,
    mock_get_users_by_service,
):
    with client_request.session_transaction() as session:
        session["team_member_mobile_change"] = "07554080636"
    client_request.post(
        "main.confirm_edit_user_mobile_number",
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _expected_status=404,
    )


def service_join_request_get_data(request_id, status, mock_requester, status_changed_by, mock_contacted_service_users):
    return {
        "id": request_id,
        "requester": {
            "id": mock_requester.get("id"),
            "name": mock_requester.get("name"),
            "belongs_to_service": [],
            "email_address": mock_requester.get("email_address"),
        },
        "service_id": SERVICE_ONE_ID,
        "created_at": datetime.utcnow(),
        "status": status,
        "status_changed_at": datetime.utcnow(),
        "status_changed_by": (
            {"id": status_changed_by.get("id"), "name": status_changed_by.get("name"), "belongs_to_service": []}
            if status_changed_by
            else None
        ),
        "reason": "",
        "contacted_service_users": mock_contacted_service_users,
    }


@pytest.fixture(scope="function")
def mock_get_service_join_request_status_data(mocker, mock_requester, mock_service_user, status):
    mocker.patch("app.notify_client.current_user", side_effect=mock_service_user)

    def _get(request_id, service_id):
        mock_contacted_service_users = [mock_service_user["id"], sample_uuid()]
        return service_join_request_get_data(
            request_id, status, mock_requester, mock_service_user, mock_contacted_service_users
        )

    return mocker.patch("app.service_api_client.get_service_join_request", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_service_join_request_not_logged_in_user(mocker):
    mock_requester = create_active_user_empty_permissions(True)
    mock_service_user = create_active_user_with_permissions(True)

    def _get(request_id, service_id):
        mock_contacted_service_users = [mock_service_user["id"]]
        return service_join_request_get_data(
            request_id, SERVICE_JOIN_REQUEST_REJECTED, mock_requester, mock_service_user, mock_contacted_service_users
        )

    return mocker.patch("app.service_api_client.get_service_join_request", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_service_join_request_user_already_joined(mocker):
    mock_requester = create_active_user_empty_permissions(True)
    mock_service_user = create_active_user_with_permissions(True)

    def _get(request_id, service_id):
        mock_contacted_service_users = [mock_service_user["id"], sample_uuid()]
        mock_request_data = service_join_request_get_data(
            request_id, "pending", mock_requester, None, mock_contacted_service_users
        )
        mock_request_data["requester"]["belongs_to_service"] = [SERVICE_ONE_ID]
        return mock_request_data

    return mocker.patch("app.service_api_client.get_service_join_request", side_effect=_get)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "mock_requester, mock_service_user, status",
    [
        (
            create_active_user_empty_permissions(True),
            create_active_user_with_permissions(True),
            "pending",
        ),
    ],
)
def test_service_join_request_pending(
    client_request,
    mocker,
    mock_requester,
    mock_service_user,
    mock_get_organisation_by_domain,
    service_one,
    status,
    mock_get_service_join_request_status_data,
):
    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    page = client_request.get(
        "main.service_join_request_approve",
        service_id=SERVICE_ONE_ID,
        request_id=sample_uuid(),
    )
    assert f"{mock_requester['name']} wants to join your service" in page.text.strip()
    assert f"{mock_requester['name']} wants to join your service" in page.select_one("h1").text.strip()
    assert (
        f"Do you want to let {mock_requester['name']} join ‘{service_one['name']}’?"
        in page.select_one("legend").text.strip()
    )

    radio_buttons = page.select("input[name=join_service_approve_request]")
    values = {button["value"] for button in radio_buttons}

    assert values == {SERVICE_JOIN_REQUEST_APPROVED, SERVICE_JOIN_REQUEST_REJECTED}

    assert normalize_spaces(page.select("form button")[0].text) == "Continue"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "endpoint, mock_requester, mock_service_user, status",
    [
        (
            "main.service_join_request_approve",
            create_active_user_empty_permissions(True),
            create_active_user_with_permissions(True),
            SERVICE_JOIN_REQUEST_APPROVED,
        ),
        (
            "main.service_join_request_choose_permissions",
            create_active_user_empty_permissions(True),
            create_active_user_with_permissions(True),
            SERVICE_JOIN_REQUEST_APPROVED,
        ),
    ],
)
def test_service_join_request_approved(
    endpoint,
    client_request,
    mocker,
    mock_requester,
    mock_service_user,
    service_one,
    mock_get_organisation_by_domain,
    status,
    mock_get_service_join_request_status_data,
):
    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        request_id=sample_uuid(),
    )
    assert f"{mock_requester['name']} has already joined your service" in page.text.strip()
    assert f"{mock_requester['name']} has already joined your service" in page.select_one("h1").text.strip()

    today_date = format_date_short(datetime.utcnow())
    assert f"{mock_service_user['name']} approved this request on {today_date}" in page.select_one("p").text.strip()


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "endpoint, mock_requester, mock_service_user, status",
    [
        (
            "main.service_join_request_approve",
            create_active_user_empty_permissions(True),
            create_active_user_with_permissions(True),
            SERVICE_JOIN_REQUEST_REJECTED,
        ),
        (
            "main.service_join_request_choose_permissions",
            create_active_user_empty_permissions(True),
            create_active_user_with_permissions(True),
            SERVICE_JOIN_REQUEST_REJECTED,
        ),
    ],
)
def test_service_join_request_rejected(
    endpoint,
    client_request,
    mocker,
    mock_requester,
    mock_service_user,
    service_one,
    mock_get_organisation_by_domain,
    status,
    mock_get_service_join_request_status_data,
):
    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        request_id=sample_uuid(),
    )
    assert f"{mock_requester['name']} join your service" in page.text.strip()
    assert f"{mock_requester['name']} join your service" in page.select_one("h1").text.strip()

    today_date = format_date_short(datetime.utcnow())
    assert (
        f"{mock_service_user['name']} already refused this request on {today_date}" in page.select_one("p").text.strip()
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "endpoint, service_one_id",
    [
        (
            "main.service_join_request_approve",
            SERVICE_ONE_ID,
        ),
        (
            "main.service_join_request_choose_permissions",
            SERVICE_ONE_ID,
        ),
    ],
)
def test_service_join_request_already_joined(
    endpoint,
    service_one_id,
    client_request,
    mocker,
    service_one,
    mock_get_organisation_by_domain,
    mock_get_service_join_request_user_already_joined,
):
    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    page = client_request.get(
        endpoint,
        service_id=service_one_id,
        request_id=sample_uuid(),
    )
    assert "This person is already a team member" in page.text.strip()
    assert "This person is already a team member" in page.select_one("h1").text.strip()
    assert "Test User With Empty Permissions is already member of ‘service one’." in page.select_one("p").text.strip()


@pytest.mark.parametrize(
    "endpoint, service_one_id",
    [
        (
            "main.service_join_request_approve",
            SERVICE_ONE_ID,
        ),
        (
            "main.service_join_request_choose_permissions",
            SERVICE_ONE_ID,
        ),
    ],
)
def test_service_join_request_should_return_403_when_approver_is_not_logged_in_user(
    endpoint,
    client_request,
    mocker,
    service_one_id,
    service_one,
    mock_get_organisation_by_domain,
    mock_get_service_join_request_not_logged_in_user,
):
    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    client_request.get(
        endpoint,
        service_id=service_one_id,
        request_id=sample_uuid(),
        _expected_status=403,
    )


@pytest.mark.parametrize(
    "mock_requester, mock_service_user, status",
    [
        (
            create_active_user_empty_permissions(True),
            create_active_user_with_permissions(True),
            "pending",
        ),
    ],
)
def test_service_join_request_redirects_to_choose_permissions_on_approve(
    client_request,
    mocker,
    mock_requester,
    mock_service_user,
    service_one,
    mock_get_organisation_by_domain,
    status,
    mock_get_service_join_request_status_data,
):
    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    request_id = sample_uuid()
    client_request.post(
        "main.service_join_request_approve",
        service_id=SERVICE_ONE_ID,
        request_id=request_id,
        _data={
            "join_service_approve_request": SERVICE_JOIN_REQUEST_APPROVED,
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_join_request_choose_permissions",
            service_id=SERVICE_ONE_ID,
            request_id=request_id,
        ),
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "mock_requester, mock_service_user, status",
    [
        (
            create_active_user_empty_permissions(True),
            create_active_user_with_permissions(True),
            "pending",
        ),
    ],
)
def test_service_join_request_shows_rejected_message_on_reject(
    client_request,
    mocker,
    mock_requester,
    mock_service_user,
    service_one,
    mock_get_organisation_by_domain,
    mock_get_service_join_request_status_data,
):
    request_id = sample_uuid()
    mock_update_service_join_requests = mocker.patch(
        "app.service_api_client.update_service_join_requests",
        return_value={},
    )

    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    page = client_request.post(
        "main.service_join_request_approve",
        service_id=SERVICE_ONE_ID,
        request_id=request_id,
        _data={
            "join_service_approve_request": SERVICE_JOIN_REQUEST_REJECTED,
        },
        _follow_redirects=True,
    )

    assert f"Tell {mock_requester['name']} you have refused their request" in page.text.strip()
    assert f"Tell {mock_requester['name']} you have refused their request" in page.select_one("h1").text.strip()
    assert (
        f"To let {mock_requester['name']} know that they cannot join your service, "
        f"email them directly at {mock_requester['email_address']}" in page.select_one("p").text.strip()
    )

    mock_update_service_join_requests.assert_called_once_with(
        request_id,
        mock_requester["id"],
        SERVICE_ONE_ID,
        status=SERVICE_JOIN_REQUEST_REJECTED,
        status_changed_by_id=current_user.id,
    )
    assert mock_update_service_join_requests.called


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "mock_requester, mock_service_user, status",
    [(create_active_user_empty_permissions(True), create_active_user_with_permissions(True), "pending")],
)
def test_service_join_request_choose_permissions(
    client_request,
    mocker,
    mock_requester,
    mock_service_user,
    service_one,
    mock_get_organisation_by_domain,
    status,
    mock_get_service_join_request_status_data,
    mock_get_template_folders,
):
    request_id = sample_uuid()

    mock_get_template_folders.return_value = [
        {"id": "folder-id-1", "name": "f1", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-2", "name": "f2", "parent_id": None, "users_with_permission": []},
    ]

    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    page = client_request.get(
        "main.service_join_request_choose_permissions",
        service_id=SERVICE_ONE_ID,
        request_id=request_id,
    )

    assert f"Choose permissions for {mock_requester['name']}" in page.text.strip()
    assert f"Choose permissions for {mock_requester['name']}" in page.select_one("h1").text.strip()
    assert f"{mock_requester['email_address']}" in page.select_one("p").text.strip()

    permission_checkboxes = page.select("input[name='permissions_field']")
    assert permission_checkboxes[0]["value"] == "view_activity"
    assert permission_checkboxes[1]["value"] == "send_messages"
    assert permission_checkboxes[2]["value"] == "manage_templates"
    assert permission_checkboxes[3]["value"] == "manage_service"
    assert permission_checkboxes[4]["value"] == "manage_api_keys"

    folder_checkboxes = page.select("input[name='folder_permissions']")
    assert len(folder_checkboxes) == 2
    assert [item["value"] for item in page.select("input[name=folder_permissions]")] == [
        "folder-id-1",
        "folder-id-2",
    ]

    assert normalize_spaces(page.select("form button")[0].text) == "Save"


@pytest.mark.parametrize(
    "service_has_email_auth, auth_options_hidden",
    [
        (False, True),
        (True, False),
    ],
)
def test_join_a_service_with_no_email_auth_hides_auth_type_options(
    client_request,
    service_has_email_auth,
    auth_options_hidden,
    service_one,
    mock_get_template_folders,
    mock_get_organisation_by_domain,
    fake_uuid,
    mocker,
):
    requester = create_active_user_empty_permissions(True)

    mocker.patch(
        "app.service_api_client.get_service_join_request",
        return_value=service_join_request_get_data(fake_uuid, "pending", requester, None, [fake_uuid]),
    )

    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    if service_has_email_auth:
        service_one["permissions"].append("email_auth")

    page = client_request.get(
        "main.service_join_request_choose_permissions",
        service_id=service_one["id"],
        request_id=fake_uuid,
    )
    assert (page.select_one("input[name=login_authentication]") is None) == auth_options_hidden


@pytest.mark.parametrize(
    "sms_option_disabled, mobile_number, expected_label",
    [
        (
            True,
            None,
            """
            Text message code
            Not available because this team member has not added a phone number to their account
            """,
        ),
        (
            False,
            "07700 900762",
            """
            Text message code
            """,
        ),
    ],
)
def test_join_a_service_user_with_no_mobile_number_cant_be_set_to_sms_auth(
    client_request,
    mock_get_template_folders,
    sms_option_disabled,
    mobile_number,
    expected_label,
    service_one,
    fake_uuid,
    mock_get_organisation_by_domain,
    mocker,
):
    requester = create_user(mobile_number=mobile_number)

    mocker.patch(
        "app.service_api_client.get_service_join_request",
        return_value=service_join_request_get_data(fake_uuid, "pending", {}, None, [fake_uuid]),
    )

    service_one["organisation"] = ORGANISATION_ID
    service_one["permissions"].append("email_auth")

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    mocker.patch("app.user_api_client.get_user", return_value=requester)

    page = client_request.get(
        "main.service_join_request_choose_permissions",
        service_id=SERVICE_ONE_ID,
        request_id=fake_uuid,
    )

    sms_auth_radio_button = page.select_one('input[value="sms_auth"]')
    assert sms_auth_radio_button.has_attr("disabled") == sms_option_disabled
    assert normalize_spaces(page.select_one("label[for=login_authentication-0]").parent.text) == normalize_spaces(
        expected_label
    )


@pytest.mark.parametrize(
    "mock_requester, mock_service_user, status",
    [(create_active_user_empty_permissions(True), create_active_user_with_permissions(True), "pending")],
)
def test_service_join_request_choose_permissions_on_save(
    client_request,
    mocker,
    mock_requester,
    mock_service_user,
    service_one,
    mock_get_organisation_by_domain,
    status,
    mock_get_service_join_request_status_data,
    mock_get_template_folders,
):
    request_id = sample_uuid()

    selected_permissions = ["send_messages", "view_activity", "manage_service"]

    mock_get_template_folders.return_value = [
        {"id": "folder-id-1", "name": "f1", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-2", "name": "f2", "parent_id": None, "users_with_permission": []},
    ]

    mock_update_service_join_requests = mocker.patch(
        "app.service_api_client.update_service_join_requests",
        return_value={},
    )

    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    client_request.post(
        "main.service_join_request_choose_permissions",
        service_id=SERVICE_ONE_ID,
        request_id=request_id,
        _data={"permissions_field": selected_permissions, "folder_permissions": ["folder-id-1", "folder-id-2"]},
        _expected_status=302,
        _expected_redirect=url_for("main.manage_users", service_id=SERVICE_ONE_ID),
    )

    mock_update_service_join_requests.assert_called_once_with(
        request_id,
        mock_requester["id"],
        SERVICE_ONE_ID,
        permissions=translate_permissions_from_ui_to_db(selected_permissions),
        status=SERVICE_JOIN_REQUEST_APPROVED,
        status_changed_by_id=current_user.id,
        folder_permissions=["folder-id-1", "folder-id-2"],
    )
    assert mock_update_service_join_requests.called


@pytest.mark.parametrize(
    "mock_requester, mock_service_user, status, auth_type",
    [
        (
            create_active_user_empty_permissions(True),
            create_active_user_with_permissions(True),
            "pending",
            "email_auth",
        ),
        (create_active_user_empty_permissions(True), create_active_user_with_permissions(True), "pending", "sms_auth"),
    ],
)
def test_service_join_request_choose_auth_type_on_save(
    client_request,
    service_one,
    mock_get_organisation_by_domain,
    mock_requester,
    mock_service_user,
    status,
    auth_type,
    mock_get_service_join_request_status_data,
    mock_get_template_folders,
    mocker,
):
    request_id = sample_uuid()

    selected_permissions = ["send_messages", "view_activity", "manage_service"]

    mock_update_service_join_requests = mocker.patch("app.service_api_client.update_service_join_requests")

    service_one["permissions"].append("email_auth")
    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    client_request.post(
        "main.service_join_request_choose_permissions",
        service_id=SERVICE_ONE_ID,
        request_id=request_id,
        _data={"permissions_field": selected_permissions, "folder_permissions": [], "login_authentication": auth_type},
        _expected_status=302,
        _expected_redirect=url_for("main.manage_users", service_id=SERVICE_ONE_ID),
    )

    mock_update_service_join_requests.assert_called_once_with(
        request_id,
        mock_requester["id"],
        SERVICE_ONE_ID,
        permissions=translate_permissions_from_ui_to_db(selected_permissions),
        status=SERVICE_JOIN_REQUEST_APPROVED,
        status_changed_by_id=current_user.id,
        folder_permissions=[],
        auth_type=auth_type,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "mock_requester, mock_service_user, status",
    [(create_active_user_empty_permissions(True), create_active_user_with_permissions(True), "pending")],
)
def test_service_join_request_refused(
    client_request,
    mocker,
    mock_requester,
    mock_service_user,
    service_one,
    mock_get_organisation_by_domain,
    status,
    mock_get_service_join_request_status_data,
):
    request_id = sample_uuid()
    mock_update_service_join_requests = mocker.patch(
        "app.service_api_client.update_service_join_requests",
        return_value={},
    )

    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    page = client_request.get(
        "main.service_join_request_refused",
        service_id=SERVICE_ONE_ID,
        request_id=request_id,
    )

    mock_update_service_join_requests.assert_called_once_with(
        request_id,
        mock_requester["id"],
        SERVICE_ONE_ID,
        status=SERVICE_JOIN_REQUEST_REJECTED,
        status_changed_by_id=current_user.id,
    )

    assert mock_update_service_join_requests.called

    assert f"Tell {mock_requester['name']} you have refused their request" in page.text.strip()
    assert f"Tell {mock_requester['name']} you have refused their request" in page.select_one("h1").text.strip()
    assert (
        f"To let {mock_requester['name']} know that they cannot join your service, "
        f"email them directly at {mock_requester['email_address']}" in page.select_one("p.govuk-body").text.strip()
    )


@pytest.mark.parametrize(
    "mock_requester, mock_service_user, status",
    [
        (
            create_active_user_empty_permissions(True),
            create_active_user_with_permissions(True),
            "pending",
        ),
    ],
)
def test_service_join_request_redirects_to_refused_on_reject(
    client_request,
    mocker,
    mock_requester,
    mock_service_user,
    service_one,
    mock_get_organisation_by_domain,
    status,
    mock_get_service_join_request_status_data,
):
    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    request_id = sample_uuid()

    client_request.post(
        "main.service_join_request_approve",
        service_id=SERVICE_ONE_ID,
        request_id=request_id,
        _data={
            "join_service_approve_request": SERVICE_JOIN_REQUEST_REJECTED,
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_join_request_refused",
            _method="GET",
            service_id=SERVICE_ONE_ID,
            request_id=request_id,
        ),
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "mock_requester, mock_service_user, status",
    [
        (
            create_active_user_empty_permissions(True),
            create_active_user_with_permissions(True),
            "pending",
        ),
    ],
)
def test_service_join_request_approved_flash_message(
    client_request,
    service_one,
    mock_get_organisation_by_domain,
    mock_requester,
    mock_get_service_join_request_status_data,
    mock_get_template_folders,
    api_user_active,
    mocker,
):
    request_id = sample_uuid()
    mocker.patch("app.user_api_client.get_user", return_value=mock_requester)
    mocker.patch("app.models.user.InvitedUsers._get_items", return_value=[])
    mocker.patch("app.user_api_client.get_users_for_service", return_value=[api_user_active])

    mocker.patch("app.service_api_client.update_service_join_requests")

    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    page = client_request.post(
        "main.service_join_request_choose_permissions",
        service_id=SERVICE_ONE_ID,
        request_id=request_id,
        _data={"permissions_field": ["send_messages"], "folder_permissions": [], "login_authentication": "email_auth"},
        _follow_redirects=True,
    )

    flash_banner = normalize_spaces(page.select_one("div.banner-default-with-tick").text)
    assert flash_banner == f"{mock_requester['name']} has joined this service"


@pytest.mark.parametrize(
    "mock_requester, mock_service_user, status",
    [
        (
            create_service_one_user(
                id=sample_uuid(), name="Test User With Empty Permissions", auth_type="webauthn_auth"
            ),
            create_active_user_with_permissions(True),
            "pending",
        )
    ],
)
def test_join_request_does_not_update_auth_type_for_webauthn_users(
    client_request,
    mocker,
    mock_requester,
    mock_service_user,
    service_one,
    mock_get_organisation_by_domain,
    status,
    mock_get_service_join_request_status_data,
    mock_get_template_folders,
):
    request_id = sample_uuid()

    selected_permissions = ["send_messages", "view_activity", "manage_service"]
    mock_user_instance = Mock()
    mock_user_instance.auth_type = "webauthn_auth"
    mock_user_instance.mobile_number = "07700 900123"
    mock_user_instance.permissions_for_service.return_value = set(selected_permissions)
    mock_user_instance.has_template_folder_permission.return_value = True
    mock_user_instance.webauthn_auth = True
    mock_user_instance.platform_admin = False

    mocker.patch("app.models.user.User.from_id", return_value=mock_user_instance)

    mock_get_template_folders.return_value = [
        {"id": "folder-id-1", "name": "f1", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-2", "name": "f2", "parent_id": None, "users_with_permission": []},
    ]

    mock_update_service_join_requests = mocker.patch(
        "app.service_api_client.update_service_join_requests",
        return_value={},
    )

    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    form_page = client_request.get(
        "main.service_join_request_choose_permissions",
        service_id=SERVICE_ONE_ID,
        request_id=request_id,
    )

    assert "Sign-in method" not in form_page.text
    assert "Text message code" not in form_page.text
    assert "Email link" not in form_page.text

    client_request.post(
        "main.service_join_request_choose_permissions",
        service_id=SERVICE_ONE_ID,
        request_id=request_id,
        # Include login_authentication in the POST data to simulate form submission,
        # but since the user uses WebAuthn, the form deletes this field before processing,
        # and the view should ignore it when updating the join request.
        _data={
            "permissions_field": selected_permissions,
            "folder_permissions": ["folder-id-1", "folder-id-2"],
        },
        _expected_status=302,
        _expected_redirect=url_for("main.manage_users", service_id=SERVICE_ONE_ID),
    )

    call_args = mock_update_service_join_requests.call_args
    kwargs = call_args.kwargs
    assert "auth_type" not in kwargs


@pytest.mark.parametrize(
    "mock_requester, mock_service_user, status",
    [
        (
            create_service_one_user(id=sample_uuid(), name="Test User With Empty Permissions", auth_type="sms_auth"),
            create_active_user_with_permissions(True),
            "pending",
        )
    ],
)
def test_join_request_updates_auth_type_for_non_webauthn_users(
    client_request,
    mocker,
    mock_requester,
    mock_service_user,
    service_one,
    mock_get_organisation_by_domain,
    status,
    mock_get_service_join_request_status_data,
    mock_get_template_folders,
):
    request_id = sample_uuid()

    selected_permissions = list(permission_mappings.keys())
    mock_user_instance = Mock()
    mock_user_instance.auth_type = "sms_auth"
    mock_user_instance.mobile_number = "07700 900123"
    mock_user_instance.has_template_folder_permission.return_value = True
    mock_user_instance.webauthn_auth = False
    mock_user_instance.platform_admin = False
    mock_user_instance.permissions_for_service.return_value = set(selected_permissions)

    mocker.patch("app.models.user.User.from_id", return_value=mock_user_instance)

    mock_get_template_folders.return_value = [
        {"id": "folder-id-1", "name": "f1", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-2", "name": "f2", "parent_id": None, "users_with_permission": []},
    ]

    mock_update_service_join_requests = mocker.patch(
        "app.service_api_client.update_service_join_requests",
        return_value={},
    )

    service_one["organisation"] = ORGANISATION_ID
    service_one["permissions"] = ["email_auth"]

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    form_page = client_request.get(
        "main.service_join_request_choose_permissions",
        service_id=SERVICE_ONE_ID,
        request_id=request_id,
    )

    assert "Sign-in method" in form_page.text
    assert "Text message code" in form_page.text
    assert "Email link" in form_page.text

    client_request.post(
        "main.service_join_request_choose_permissions",
        service_id=SERVICE_ONE_ID,
        request_id=request_id,
        _data={
            "permissions_field": selected_permissions,
            "folder_permissions": ["folder-id-1", "folder-id-2"],
            "login_authentication": "sms_auth",
        },
        _expected_status=302,
        _expected_redirect=url_for("main.manage_users", service_id=SERVICE_ONE_ID),
    )

    call_args = mock_update_service_join_requests.call_args
    kwargs = call_args.kwargs

    assert kwargs["auth_type"] == "sms_auth"
    assert kwargs["permissions"] is not None
    assert kwargs["folder_permissions"] == ["folder-id-1", "folder-id-2"]

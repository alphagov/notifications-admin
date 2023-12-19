import pytest
from flask import url_for
from freezegun import freeze_time

from tests import organisation_json, service_json
from tests.conftest import (
    ORGANISATION_ID,
    SERVICE_ONE_ID,
    SERVICE_TWO_ID,
    create_active_user_empty_permissions,
    create_active_user_manage_template_permissions,
    create_active_user_view_permissions,
    create_active_user_with_permissions,
    create_user,
    normalize_spaces,
)


def test_choose_service_to_join(
    mocker,
    client_request,
):
    mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=organisation_json(can_ask_to_join_a_service=True),
    )
    mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[
            service_json(SERVICE_ONE_ID, "service one", restricted=False),
            service_json(SERVICE_TWO_ID, "service two", restricted=False),
            service_json("1234", "service three (trial mode)"),
        ],
    )
    mocker.patch(
        "app.models.user.Users.client_method",
        return_value=[
            create_user(permissions={SERVICE_TWO_ID: ["manage_service"]}),
            create_user(permissions={SERVICE_TWO_ID: []}),
        ],
    )
    page = client_request.get(
        "main.choose_service_to_join",
        service_to_join_id=SERVICE_ONE_ID,
    )
    assert normalize_spaces(page.select_one("main p").text) == (
        "These are all the Test Organisation teams who have a live service on Notify."
    )
    assert [normalize_spaces(item.text) for item in page.select(".browse-list-item")] == [
        "service one You are already a team member of this service",
        "service two 1 team member",
    ]
    assert [link["href"] for link in page.select(".browse-list-item a")] == [
        url_for("main.join_service", service_to_join_id=SERVICE_ONE_ID),
        url_for("main.join_service", service_to_join_id=SERVICE_TWO_ID),
    ]


def test_cannot_join_service_without_organisation(client_request):
    client_request.get(
        "main.join_service",
        service_to_join_id=SERVICE_ONE_ID,
        _expected_status=403,
    )


@pytest.mark.parametrize(
    "can_ask_to_join_a_service",
    (
        False,
        pytest.param(True, marks=pytest.mark.xfail),
    ),
)
def test_cannot_join_service_without_organisation_permission(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    can_ask_to_join_a_service,
):
    service_one["organisation"] = fake_uuid
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(can_ask_to_join_a_service=can_ask_to_join_a_service),
    )
    mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=organisation_json(can_ask_to_join_a_service=can_ask_to_join_a_service),
    )
    client_request.get(
        "main.choose_service_to_join",
        _expected_status=403,
    )
    client_request.get(
        "main.join_service",
        service_to_join_id=SERVICE_ONE_ID,
        _expected_status=403,
    )


def test_cannot_join_service_for_different_organisation(
    mocker,
    client_request,
    service_one,
    fake_uuid,
):
    service_one["organisation"] = fake_uuid
    mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=organisation_json(id_="1234", can_ask_to_join_a_service=True),
    )
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_="4321", can_ask_to_join_a_service=True),
    )
    client_request.get(
        "main.join_service",
        service_to_join_id=SERVICE_ONE_ID,
        _expected_status=403,
    )


@freeze_time("2023-02-03 01:00")
def test_page_lists_team_members_of_service(
    mocker,
    client_request,
    fake_uuid,
    service_one,
    mock_get_organisation_by_domain,
):
    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    manage_service_user_1 = create_active_user_with_permissions()
    manage_service_user_2 = create_active_user_with_permissions()
    manage_service_user_1["name"] = "Manage service user 1"
    manage_service_user_2["name"] = "Manage service user 2"
    manage_service_user_1["logged_in_at"] = "2023-01-02 01:00"
    manage_service_user_2["logged_in_at"] = "2023-02-03 01:00"

    mock_get_users = mocker.patch(
        "app.models.user.Users.client_method",
        return_value=[
            # These three users should not appear on the page
            create_active_user_empty_permissions(),
            create_active_user_manage_template_permissions(),
            create_active_user_view_permissions(),
            # These two users should appear on the page
            manage_service_user_1,
            manage_service_user_2,
        ],
    )

    page = client_request.get("main.join_service", service_to_join_id=SERVICE_ONE_ID)

    assert normalize_spaces(page.select_one("h1").text) == "Ask to join service one"

    assert [
        (
            checkbox["value"],
            normalize_spaces(label.text),
            normalize_spaces(hint.text),
        )
        for checkbox, label, hint in zip(
            page.select("input[type=checkbox][name=users]"),
            page.select(".govuk-label"),
            page.select(".govuk-hint"),
        )
    ] == [
        (
            manage_service_user_1["id"],
            "Manage service user 1",
            "Last used Notify 2 January",
        ),
        (
            manage_service_user_2["id"],
            "Manage service user 2",
            "Last used Notify today",
        ),
    ]

    assert page.select_one("textarea")["name"] == page.select_one("textarea")["id"] == "reason"
    assert normalize_spaces(page.select_one("label[for=reason]").text) == "Explain why you need access (optional)"

    mock_get_users.assert_called_once_with(SERVICE_ONE_ID)


def test_page_redirects_on_post(
    mocker,
    client_request,
    mock_request_invite_for,
    fake_uuid,
    service_one,
    mock_get_organisation_by_domain,
):
    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.models.organisation.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )
    current_user = create_active_user_with_permissions(with_unique_id=True)
    manage_service_user_1 = create_active_user_with_permissions(with_unique_id=True)
    manage_service_user_2 = create_active_user_with_permissions(with_unique_id=True)
    manage_service_user_1["logged_in_at"] = "2023-01-02 01:00"
    manage_service_user_2["logged_in_at"] = "2023-02-03 01:00"

    mocker.patch(
        "app.models.user.Users.client_method",
        return_value=[
            manage_service_user_1,
            manage_service_user_2,
        ],
    )

    client_request.login(current_user)
    client_request.post(
        "main.join_service",
        service_to_join_id=SERVICE_ONE_ID,
        _expected_redirect=url_for(
            "main.join_service_requested",
            service_to_join_id=SERVICE_ONE_ID,
            number_of_users_emailed=1,
        ),
        _data={
            "users": manage_service_user_1["id"],
            "reason": "Let me in",
        },
    )

    mock_request_invite_for.assert_called_once_with(
        user_to_invite_id=current_user["id"],
        service_managers_ids=[
            manage_service_user_1["id"],
        ],
        reason="Let me in",
        service_id=SERVICE_ONE_ID,
    )

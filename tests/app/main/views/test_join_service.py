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
    create_service_two_user_with_permissions,
    normalize_spaces,
)


def test_join_service_choose_service(
    client_request,
    mocker,
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
    page = client_request.get(
        "main.join_service_choose_service",
        service_to_join_id=SERVICE_ONE_ID,
    )
    assert normalize_spaces(page.select_one("main p").text) == "Test Organisation has 2 live services"
    assert [normalize_spaces(item.text) for item in page.select(".browse-list-item")] == [
        "service one You are already a team member of this service",
        "service two",
    ]
    assert [link["href"] for link in page.select(".browse-list-item a")] == [
        url_for("main.join_service_ask", service_to_join_id=SERVICE_ONE_ID),
        url_for("main.join_service_ask", service_to_join_id=SERVICE_TWO_ID),
    ]


def test_cannot_join_service_without_organisation(client_request):
    client_request.get(
        "main.join_service_ask",
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
    client_request,
    service_one,
    fake_uuid,
    can_ask_to_join_a_service,
    mocker,
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
        "main.join_service_choose_service",
        _expected_status=403,
    )
    client_request.get(
        "main.join_service_ask",
        service_to_join_id=SERVICE_ONE_ID,
        _expected_status=403,
    )


def test_cannot_join_service_for_different_organisation(
    client_request,
    service_one,
    fake_uuid,
    mocker,
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
        "main.join_service_ask",
        service_to_join_id=SERVICE_ONE_ID,
        _expected_status=403,
    )


def test_redirect_if_already_member_of_service(
    client_request,
    mock_request_invite_for,
    service_one,
    mock_get_organisation_by_domain,
    mocker,
):
    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.models.organisation.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )
    current_user = create_active_user_with_permissions(with_unique_id=True)

    client_request.login(current_user)
    client_request.post(
        "main.join_service_ask",
        service_to_join_id=SERVICE_ONE_ID,
        _expected_redirect=url_for(
            "main.service_dashboard",
            service_id=SERVICE_ONE_ID,
        ),
    )


@freeze_time("2023-02-03 01:00")
def test_page_lists_team_members_of_service(
    client_request,
    service_one,
    mock_get_organisation_by_domain,
    mocker,
):
    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )

    current_user = create_service_two_user_with_permissions()

    manage_service_user_1 = create_active_user_with_permissions()
    manage_service_user_2 = create_active_user_with_permissions()
    manage_service_user_3 = create_active_user_with_permissions()
    manage_service_user_1["name"] = "Manage service user 1"
    manage_service_user_2["name"] = "Manage service user 2"
    manage_service_user_3["name"] = "Manage service user 3"
    manage_service_user_1["logged_in_at"] = "2023-01-02 01:00"
    manage_service_user_2["logged_in_at"] = "2023-02-03 01:00"
    manage_service_user_3["logged_in_at"] = None

    client_request.login(current_user)

    mock_get_users = mocker.patch(
        "app.models.user.Users._get_items",
        return_value=[
            # These three users should not appear on the page
            create_active_user_empty_permissions(),
            create_active_user_manage_template_permissions(),
            create_active_user_view_permissions(),
            # These two users should appear on the page
            manage_service_user_1,
            manage_service_user_2,
            manage_service_user_3,
        ],
    )

    page = client_request.get("main.join_service_ask", service_to_join_id=SERVICE_ONE_ID)

    assert normalize_spaces(page.select_one("h1").text) == "Ask to join this service"
    assert normalize_spaces(page.select_one("main p").text) == "You’re asking to join ‘service one’."

    assert [
        (
            checkbox["value"],
            normalize_spaces(label.text),
            normalize_spaces(hint.text),
        )
        for checkbox, label, hint in zip(
            page.select("#users input[type=checkbox][name=users]"),
            page.select("#users .govuk-label"),
            page.select("#users .govuk-hint"),
            strict=True,
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
        (
            manage_service_user_3["id"],
            "Manage service user 3",
            "Never used Notify",
        ),
    ]

    assert page.select_one("textarea")["name"] == page.select_one("textarea")["id"] == "reason"
    assert (
        normalize_spaces(page.select_one("label[for=reason]").text)
        == "Tell them why you want to join this service (optional)"
    )
    assert not page.select("#reason-hint")

    mock_get_users.assert_called_once_with(SERVICE_ONE_ID)


def test_page_redirects_on_post(
    client_request,
    mock_request_invite_for,
    service_one,
    service_two,
    mock_get_organisation_by_domain,
    mocker,
):
    service_one["organisation"] = ORGANISATION_ID
    mocker.patch(
        "app.models.organisation.organisations_client.get_organisation",
        return_value=organisation_json(id_=ORGANISATION_ID, can_ask_to_join_a_service=True),
    )
    current_user = create_service_two_user_with_permissions(with_unique_id=True)
    manage_service_user_1 = create_active_user_with_permissions(with_unique_id=True)
    manage_service_user_2 = create_active_user_with_permissions(with_unique_id=True)
    manage_service_user_1["logged_in_at"] = "2023-01-02 01:00"
    manage_service_user_2["logged_in_at"] = "2023-02-03 01:00"

    mocker.patch(
        "app.models.user.Users._get_items",
        return_value=[
            manage_service_user_1,
            manage_service_user_2,
        ],
    )

    client_request.login(current_user)
    client_request.post(
        "main.join_service_ask",
        service_to_join_id=SERVICE_ONE_ID,
        _expected_redirect=url_for(
            "main.join_service_you_have_asked",
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


def test_confirmation_page(
    client_request,
):
    page = client_request.get(
        "main.join_service_you_have_asked",
        service_to_join_id=SERVICE_ONE_ID,
        number_of_users_emailed=1,
    )

    assert normalize_spaces(page.select_one("h1").text) == "You have asked to join an existing service"
    assert [normalize_spaces(p.text) for p in page.select("main p")] == [
        "We have sent your request to 1 member of ‘service one’.",
        "We’ve also sent you a confirmation email.",
        "You’ll get another email if your request is approved.",
        "Back to your services",
    ]

    assert [(normalize_spaces(link.text), link["href"]) for link in page.select("main a")] == [
        ("Back to your services", url_for("main.your_services"))
    ]

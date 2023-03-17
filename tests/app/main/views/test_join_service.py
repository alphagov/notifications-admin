from flask import url_for
from freezegun import freeze_time

from tests.conftest import (
    SERVICE_ONE_ID,
    create_active_user_empty_permissions,
    create_active_user_manage_template_permissions,
    create_active_user_view_permissions,
    create_active_user_with_permissions,
    normalize_spaces,
)


@freeze_time("2023-02-03 01:00")
def test_page_lists_team_members_of_service(
    mocker,
    client_request,
):
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
    assert normalize_spaces(page.select_one("label[for=reason]").text) == "Explain why you need access"

    mock_get_users.assert_called_once_with(SERVICE_ONE_ID)


def test_page_redirects_on_post(
    mocker,
    client_request,
    mock_request_invite_for,
    fake_uuid,
):
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
        from_user_ids=[
            manage_service_user_1["id"],
        ],
        reason="Let me in",
        service_id=SERVICE_ONE_ID,
    )

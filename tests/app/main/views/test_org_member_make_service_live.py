from unittest import mock

import pytest
from flask import url_for
from freezegun import freeze_time

from app.constants import PERMISSION_CAN_MAKE_SERVICES_LIVE
from tests.conftest import (
    ORGANISATION_ID,
    SERVICE_ONE_ID,
    create_user,
    normalize_spaces,
    sample_uuid,
)

test_user_auth_combinations = (
    """
        user,
        organisation_can_approve_own_go_live_requests,
        service_has_active_go_live_request,
        service_is_active,
        expected_status,
    """,
    (
        (
            # A user who is a member of the organisation
            create_user(
                id=sample_uuid(),
                organisations=[ORGANISATION_ID],
                organisation_permissions={ORGANISATION_ID: [PERMISSION_CAN_MAKE_SERVICES_LIVE]},
            ),
            True,
            True,
            True,
            200,
        ),
        (
            # A platform admin users who is not a member of the organisation
            create_user(id=sample_uuid(), platform_admin=True),
            True,
            True,
            True,
            200,
        ),
        (
            # User who is a not an organisation team member can’t approve go live requests
            create_user(id=sample_uuid()),
            True,
            True,
            True,
            403,
        ),
        (
            # If the organisation can’t approve its own go live requests then the user is blocked
            create_user(
                id=sample_uuid(),
                organisations=[ORGANISATION_ID],
                organisation_permissions={ORGANISATION_ID: [PERMISSION_CAN_MAKE_SERVICES_LIVE]},
            ),
            False,
            True,
            True,
            403,
        ),
        (
            # If the service doesn’t have an active go live request then the user is blocked
            create_user(
                id=sample_uuid(),
                organisations=[ORGANISATION_ID],
                organisation_permissions={ORGANISATION_ID: [PERMISSION_CAN_MAKE_SERVICES_LIVE]},
            ),
            True,
            False,
            True,
            403,
        ),
        (
            # If the user doesn't have the "can make services live" permission then the user is blocked
            create_user(id=sample_uuid(), organisations=[ORGANISATION_ID], organisation_permissions={}),
            True,
            False,
            True,
            403,
        ),
        (
            # If the service is not active then the user is blocked
            create_user(id=sample_uuid(), platform_admin=True),
            True,
            True,
            False,
            403,
        ),
    ),
)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(*test_user_auth_combinations)
def test_get_org_member_make_service_live_start(
    client_request,
    service_one,
    organisation_one,
    user,
    organisation_can_approve_own_go_live_requests,
    service_has_active_go_live_request,
    service_is_active,
    expected_status,
    mocker,
):
    organisation_one["can_approve_own_go_live_requests"] = organisation_can_approve_own_go_live_requests

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    service_one["has_active_go_live_request"] = service_has_active_go_live_request
    service_one["organisation"] = ORGANISATION_ID
    service_one["volume_letter"] = None
    service_one["active"] = service_is_active

    client_request.login(user)

    page = client_request.get(
        "main.org_member_make_service_live_start",
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_status,
    )

    if expected_status == 200:
        assert (
            normalize_spaces(page.select_one("main p")) == "Test User has sent a request to go live for ‘service one’."
        )
        assert [normalize_spaces(li) for li in page.select_one("main ul").select("li")] == [
            "111,111 emails per year",
            "222,222 text messages per year",
            "No letters",
        ]

        button = page.select_one("a.govuk-button")
        assert button.text.strip() == "Continue"
        assert button.get("href") == f"/services/{SERVICE_ONE_ID}/make-service-live/unique-service"


def test_make_service_live_start_with_no_organisation(
    client_request,
    service_one,
    mocker,
):
    service_one["has_active_go_live_request"] = True
    service_one["organisation"] = None

    client_request.get(
        "main.org_member_make_service_live_start",
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_make_service_live_start_with_no_organisation_platform_admin(
    client_request,
    service_one,
    platform_admin_user,
    mocker,
):
    service_one["has_active_go_live_request"] = True
    service_one["organisation"] = None
    client_request.login(platform_admin_user)

    page = client_request.get(
        "main.org_member_make_service_live_start",
        service_id=SERVICE_ONE_ID,
        _expected_status=410,
    )

    assert normalize_spaces(page.select_one("h1").text) == "This service does not belong to an organisation"
    assert page.select_one("main a")["href"] == url_for(
        ".link_service_to_organisation",
        service_id=SERVICE_ONE_ID,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(*test_user_auth_combinations)
def test_get_org_member_make_service_live_service_name(
    client_request,
    service_one,
    organisation_one,
    user,
    organisation_can_approve_own_go_live_requests,
    service_has_active_go_live_request,
    service_is_active,
    expected_status,
    mocker,
):
    organisation_one["can_approve_own_go_live_requests"] = organisation_can_approve_own_go_live_requests

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    service_one["has_active_go_live_request"] = service_has_active_go_live_request
    service_one["organisation"] = ORGANISATION_ID
    service_one["volume_letter"] = None
    service_one["active"] = service_is_active

    client_request.login(user)

    page = client_request.get(
        "main.org_member_make_service_live_service_name",
        service_id=SERVICE_ONE_ID,
        unique="yes",
        _expected_status=expected_status,
    )

    if expected_status == 200:
        assert "Check the service name" in normalize_spaces(page.select_one("main").text)

        form = page.select_one("form")
        button = form.select_one("button")
        assert button.text.strip() == "Continue"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_post_org_member_make_service_live_service_name_error_summary(
    client_request,
    service_one,
    organisation_one,
    mocker,
):
    user = create_user(
        id=sample_uuid(),
        organisations=[ORGANISATION_ID],
        organisation_permissions={ORGANISATION_ID: [PERMISSION_CAN_MAKE_SERVICES_LIVE]},
    )
    organisation_one["can_approve_own_go_live_requests"] = True

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    service_one["has_active_go_live_request"] = True
    service_one["organisation"] = ORGANISATION_ID
    service_one["volume_letter"] = None

    client_request.login(user)

    page = client_request.post(
        "main.org_member_make_service_live_service_name",
        service_id=SERVICE_ONE_ID,
        unique="yes",
        _expected_status=200,
        _data={},
    )

    error_summary = page.select_one(".govuk-error-summary")
    assert "There is a problem" in error_summary.text
    assert "Select ‘yes’ if recipients will understand the service name" in error_summary.text


@pytest.mark.parametrize(
    "form_data, query_args, expected_redirect_url, expected_notify_calls",
    (
        (
            {"enabled": True},  # service name is clear/easy to understand
            {"unique": "yes"},  # service has a unique purpose
            f"/services/{SERVICE_ONE_ID}/make-service-live/decision?name=ok&unique=yes",
            [],
        ),
        (
            {"enabled": True},  # service name is clear/easy to understand
            {"unique": "unsure"},  # user is unsure if service is unique
            f"/services/{SERVICE_ONE_ID}/make-service-live/contact-user?name=ok&unique=unsure",
            [
                mock.call(
                    service_id=SERVICE_ONE_ID,
                    service_name="service one",
                    to="test@user.gov.uk",
                    check_if_unique=True,
                    unclear_service_name=False,
                )
            ],
        ),
        (
            {"enabled": True},  # service name is clear/easy to understand
            {"unique": "no"},  # user believes service is not unique within the org
            f"/services/{SERVICE_ONE_ID}/make-service-live/decision?unique=no",
            [],
        ),
        (
            {"enabled": False},  # service name is unclear/hard to understandable
            {"unique": "yes"},  # service has a unique purpose
            f"/services/{SERVICE_ONE_ID}/make-service-live/contact-user?name=bad&unique=yes",
            [
                mock.call(
                    service_id=SERVICE_ONE_ID,
                    service_name="service one",
                    to="test@user.gov.uk",
                    check_if_unique=False,
                    unclear_service_name=True,
                )
            ],
        ),
        (
            {"enabled": False},  # service name is unclear/hard to understandable
            {"unique": "no"},  # user believes service is not unique within the org
            f"/services/{SERVICE_ONE_ID}/make-service-live/decision?unique=no",
            [],
        ),
        (
            {"enabled": False},  # service name is unclear/hard to understandable
            {"unique": "unsure"},  # user is unsure if service is unique
            f"/services/{SERVICE_ONE_ID}/make-service-live/contact-user?name=bad&unique=unsure",
            [
                mock.call(
                    service_id=SERVICE_ONE_ID,
                    service_name="service one",
                    to="test@user.gov.uk",
                    check_if_unique=True,
                    unclear_service_name=True,
                )
            ],
        ),
    ),
)
def test_post_org_member_make_service_live_service_name(
    client_request,
    service_one,
    organisation_one,
    form_data,
    query_args,
    expected_redirect_url,
    expected_notify_calls,
    mocker,
):
    user = create_user(
        id=sample_uuid(),
        organisations=[ORGANISATION_ID],
        organisation_permissions={ORGANISATION_ID: [PERMISSION_CAN_MAKE_SERVICES_LIVE]},
    )
    organisation_one["can_approve_own_go_live_requests"] = True

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)
    mock_notify = mocker.patch("app.organisations_client.notify_org_member_about_next_steps_of_go_live_request")

    service_one["has_active_go_live_request"] = True
    service_one["organisation"] = ORGANISATION_ID
    service_one["volume_letter"] = None

    client_request.login(user)

    client_request.post(
        "main.org_member_make_service_live_service_name",
        service_id=SERVICE_ONE_ID,
        **query_args,
        _expected_redirect=expected_redirect_url,
        _data=form_data,
    )

    assert mock_notify.call_args_list == expected_notify_calls


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(*test_user_auth_combinations)
def test_get_org_member_make_service_live_unique_service(
    client_request,
    service_one,
    organisation_one,
    user,
    organisation_can_approve_own_go_live_requests,
    service_has_active_go_live_request,
    service_is_active,
    expected_status,
    mocker,
):
    organisation_one["can_approve_own_go_live_requests"] = organisation_can_approve_own_go_live_requests

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    service_one["has_active_go_live_request"] = service_has_active_go_live_request
    service_one["organisation"] = ORGANISATION_ID
    service_one["volume_letter"] = None
    service_one["active"] = service_is_active

    client_request.login(user)

    page = client_request.get(
        "main.org_member_make_service_live_check_unique",
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_status,
    )

    if expected_status == 200:
        assert "Confirm this service is unique" in normalize_spaces(page.select_one("main").text)

        form = page.select_one("form")
        button = form.select_one("button")
        assert button.text.strip() == "Continue"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_post_org_member_make_service_live_unique_service_error_summary(
    client_request,
    service_one,
    organisation_one,
    mocker,
):
    user = create_user(
        id=sample_uuid(),
        organisations=[ORGANISATION_ID],
        organisation_permissions={ORGANISATION_ID: [PERMISSION_CAN_MAKE_SERVICES_LIVE]},
    )
    organisation_one["can_approve_own_go_live_requests"] = True

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    service_one["has_active_go_live_request"] = True
    service_one["organisation"] = ORGANISATION_ID
    service_one["volume_letter"] = None

    client_request.login(user)

    page = client_request.post(
        "main.org_member_make_service_live_check_unique",
        service_id=SERVICE_ONE_ID,
        _expected_status=200,
        _data={},
    )

    error_summary = page.select_one(".govuk-error-summary")
    assert "There is a problem" in error_summary.text
    assert "Select ‘yes’ if this service is unique" in error_summary.text


@pytest.mark.parametrize(
    "request_url, data, expected_redirect_url",
    (
        (
            f"/services/{SERVICE_ONE_ID}/make-service-live/unique-service",
            {"is_unique": "yes"},
            f"/services/{SERVICE_ONE_ID}/make-service-live/service-name?unique=yes",
        ),
        (
            f"/services/{SERVICE_ONE_ID}/make-service-live/unique-service",
            {"is_unique": "unsure"},
            f"/services/{SERVICE_ONE_ID}/make-service-live/service-name?unique=unsure",
        ),
        (
            f"/services/{SERVICE_ONE_ID}/make-service-live/unique-service",
            {"is_unique": "no"},
            f"/services/{SERVICE_ONE_ID}/make-service-live/decision?unique=no",
        ),
    ),
)
def test_post_org_member_make_service_live_unique_service(
    client_request,
    service_one,
    organisation_one,
    request_url,
    data,
    expected_redirect_url,
    mocker,
):
    user = create_user(
        id=sample_uuid(),
        organisations=[ORGANISATION_ID],
        organisation_permissions={ORGANISATION_ID: [PERMISSION_CAN_MAKE_SERVICES_LIVE]},
    )
    organisation_one["can_approve_own_go_live_requests"] = True

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    service_one["has_active_go_live_request"] = True
    service_one["organisation"] = ORGANISATION_ID
    service_one["volume_letter"] = None

    client_request.login(user)

    client_request.post_url(
        request_url,
        _expected_redirect=expected_redirect_url,
        _data=data,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "data, expected_redirect",
    (
        ({}, f"/services/{SERVICE_ONE_ID}/make-service-live"),
        ({"name": "ok", "unique": "yes"}, f"/services/{SERVICE_ONE_ID}/make-service-live/decision?name=ok&unique=yes"),
        ({"name": "bad", "unique": "yes"}, None),
        ({"name": "ok", "unique": "no"}, f"/services/{SERVICE_ONE_ID}/make-service-live/decision?name=ok&unique=no"),
        ({"name": "bad", "unique": "no"}, f"/services/{SERVICE_ONE_ID}/make-service-live/decision?name=bad&unique=no"),
        ({"name": "ok", "unique": "unsure"}, None),
        ({"name": "bad", "unique": "unsure"}, None),
    ),
)
@pytest.mark.parametrize(*test_user_auth_combinations)
def test_get_org_member_make_service_live_contact_user(
    client_request,
    service_one,
    organisation_one,
    user,
    organisation_can_approve_own_go_live_requests,
    service_has_active_go_live_request,
    service_is_active,
    expected_status,
    data,
    expected_redirect,
    mocker,
):
    organisation_one["can_approve_own_go_live_requests"] = organisation_can_approve_own_go_live_requests

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    service_one["has_active_go_live_request"] = service_has_active_go_live_request
    service_one["organisation"] = ORGANISATION_ID
    service_one["volume_letter"] = None
    service_one["active"] = service_is_active

    client_request.login(user)

    page = client_request.get(
        "main.org_member_make_service_live_contact_user",
        service_id=SERVICE_ONE_ID,
        **data,
        _expected_redirect=expected_redirect if expected_status == 200 else None,
        _expected_status=expected_status,
    )

    if expected_status == 200 and not expected_redirect:
        assert "Contact the team member that made the request to go live" in normalize_spaces(
            page.select_one("main").text
        )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(*test_user_auth_combinations)
def test_get_org_member_make_service_live_decision(
    client_request,
    service_one,
    organisation_one,
    user,
    organisation_can_approve_own_go_live_requests,
    service_has_active_go_live_request,
    service_is_active,
    expected_status,
    mocker,
):
    organisation_one["can_approve_own_go_live_requests"] = organisation_can_approve_own_go_live_requests

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    service_one["has_active_go_live_request"] = service_has_active_go_live_request
    service_one["organisation"] = ORGANISATION_ID
    service_one["volume_letter"] = None
    service_one["active"] = service_is_active

    client_request.login(user)

    page = client_request.get(
        "main.org_member_make_service_live_decision",
        service_id=SERVICE_ONE_ID,
        unique="yes",
        name="ok",
        _expected_status=expected_status,
    )

    if expected_status == 200:
        assert [
            (radio.select_one("input[type=radio]")["value"], normalize_spaces(radio.select_one("label").text))
            for radio in page.select(".govuk-radios__item")
        ] == [
            ("True", "Approve the request and make this service live"),
            ("False", "Reject the request"),
        ]


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "post_data, expected_error_message",
    (
        ({}, "Select approve or reject"),
        ({"enabled": False}, "Enter a reason"),
    ),
)
def test_post_org_member_make_service_live_decision_error_summary(
    client_request,
    service_one,
    organisation_one,
    post_data,
    expected_error_message,
    mocker,
):
    user = create_user(
        id=sample_uuid(),
        organisations=[ORGANISATION_ID],
        organisation_permissions={ORGANISATION_ID: [PERMISSION_CAN_MAKE_SERVICES_LIVE]},
    )
    organisation_one["can_approve_own_go_live_requests"] = True

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    service_one["has_active_go_live_request"] = True
    service_one["organisation"] = ORGANISATION_ID
    service_one["volume_letter"] = None

    client_request.login(user)

    page = client_request.post(
        "main.org_member_make_service_live_decision",
        service_id=SERVICE_ONE_ID,
        name="ok",
        unique="yes",
        _expected_status=200,
        _data=post_data,
    )

    error_summary = page.select_one(".govuk-error-summary")
    assert "There is a problem" in error_summary.text
    assert expected_error_message in error_summary.text


@pytest.mark.parametrize(
    "query_args, post_data, expected_arguments_to_update_service, should_notify",
    (
        (
            {"name": "ok", "unique": "yes"},
            {"enabled": True},
            {
                "email_message_limit": 250_000,
                "sms_message_limit": 250_000,
                "letter_message_limit": 20_000,
                "restricted": False,
                "go_live_at": "2022-12-22 12:12:12",
                "has_active_go_live_request": False,
            },
            False,
        ),
        (
            {"name": "ok", "unique": "yes"},
            {"enabled": False, "rejection_reason": "It's a stinker"},
            {
                "email_message_limit": 50,
                "sms_message_limit": 50,
                "letter_message_limit": 50,
                "restricted": True,
                "go_live_at": None,
                "has_active_go_live_request": False,
            },
            True,
        ),
    ),
)
@freeze_time("2022-12-22 12:12:12")
def test_post_org_member_make_service_live_decision(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_organisation,
    mock_update_service,
    query_args,
    post_data,
    expected_arguments_to_update_service,
    should_notify,
    mocker,
):
    service_one["has_active_go_live_request"] = True
    service_one["organisation"] = ORGANISATION_ID
    mock_notify = mocker.patch("app.organisations_client.notify_service_member_of_rejected_go_live_request")

    client_request.login(platform_admin_user)

    client_request.post(
        "main.org_member_make_service_live_decision",
        service_id=SERVICE_ONE_ID,
        **query_args,
        _data=post_data,
        _expected_redirect=url_for("main.organisation_dashboard", org_id=ORGANISATION_ID),
    )

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        **expected_arguments_to_update_service,
    )

    if should_notify:
        assert mock_notify.call_args_list == [
            mocker.call(
                service_id=service_one["id"],
                service_member_name="Platform admin user",
                service_name="service one",
                organisation_name="Test organisation",
                rejection_reason="It's a stinker",
                organisation_team_member_name="Platform admin user",
                organisation_team_member_email="platform@admin.gov.uk",
            )
        ]

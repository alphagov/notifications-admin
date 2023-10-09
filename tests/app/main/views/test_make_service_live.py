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

pytest_user_auth_combinations = (
    "user, organisation_can_approve_own_go_live_requests, service_has_active_go_live_request, expected_status",
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
            200,
        ),
        (
            # A platform admin users who is not a member of the organisation
            create_user(id=sample_uuid(), platform_admin=True),
            True,
            True,
            200,
        ),
        (
            # User who is a not an organisation team member can’t approve go live requests
            create_user(id=sample_uuid()),
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
            403,
        ),
        (
            # If the user doesn't have the "can make services live" permission then the user is blocked
            create_user(id=sample_uuid(), organisations=[ORGANISATION_ID], organisation_permissions={}),
            True,
            False,
            403,
        ),
    ),
)


@pytest.mark.parametrize(*pytest_user_auth_combinations)
def test_get_make_service_live_page(
    mocker,
    client_request,
    service_one,
    organisation_one,
    user,
    organisation_can_approve_own_go_live_requests,
    service_has_active_go_live_request,
    expected_status,
):
    organisation_one["can_approve_own_go_live_requests"] = organisation_can_approve_own_go_live_requests

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    service_one["has_active_go_live_request"] = service_has_active_go_live_request
    service_one["organisation"] = ORGANISATION_ID
    service_one["volume_letter"] = None

    client_request.login(user)

    page = client_request.get(
        "main.make_service_live",
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_status,
    )

    if expected_status == 200:
        assert (
            normalize_spaces(page.select_one("main p")) == "Test User has requested for this service to be made live."
        )
        assert [normalize_spaces(li) for li in page.select("main li")] == [
            "111,111 emails per year",
            "222,222 text messages per year",
            "No letters",
        ]

        assert [
            (radio.select_one("input[type=radio]")["value"], normalize_spaces(radio.select_one("label").text))
            for radio in page.select(".govuk-radios__item")
        ] == [
            ("True", "Approve the request and make this service live"),
            ("False", "Reject the request"),
        ]


def test_get_make_service_live_page_without_org(
    client_request,
    service_one,
    organisation_one,
):
    user = create_user(id=sample_uuid(), platform_admin=True)

    service_one["has_active_go_live_request"] = True
    service_one["volume_letter"] = None

    client_request.login(user)

    page = client_request.get(
        "main.make_service_live",
        service_id=SERVICE_ONE_ID,
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one("a#link-org")) == "link an organisation"


@pytest.mark.parametrize(
    "method",
    ("get", "post"),
)
@pytest.mark.parametrize(
    "user",
    (
        create_user(id=sample_uuid(), organisations=[ORGANISATION_ID]),
        create_user(id=sample_uuid(), platform_admin=True),
    ),
)
def test_service_is_already_live(
    mocker,
    client_request,
    service_one,
    organisation_one,
    mock_update_service,
    user,
    method,
):
    organisation_one["can_approve_own_go_live_requests"] = True
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    service_one["restricted"] = False
    service_one["organisation"] = ORGANISATION_ID

    client_request.login(user)

    page = getattr(client_request, method)(
        "main.make_service_live",
        service_id=SERVICE_ONE_ID,
        _expected_status=410,
    )

    assert normalize_spaces(page.select_one("h1").text) == "This service is already live"
    assert mock_update_service.called is False


@pytest.mark.parametrize(
    "post_data, expected_arguments_to_update_service",
    (
        (
            True,
            {
                "email_message_limit": 250_000,
                "sms_message_limit": 250_000,
                "letter_message_limit": 20_000,
                "restricted": False,
                "go_live_at": "2022-12-22 12:12:12",
                "has_active_go_live_request": False,
            },
        ),
        (
            False,
            {
                "email_message_limit": 50,
                "sms_message_limit": 50,
                "letter_message_limit": 50,
                "restricted": True,
                "go_live_at": None,
                "has_active_go_live_request": False,
            },
        ),
    ),
)
@freeze_time("2022-12-22 12:12:12")
def test_post_make_service_live_page(
    mocker,
    client_request,
    platform_admin_user,
    service_one,
    mock_get_organisation,
    mock_update_service,
    post_data,
    expected_arguments_to_update_service,
):
    service_one["has_active_go_live_request"] = True
    service_one["organisation"] = ORGANISATION_ID

    client_request.login(platform_admin_user)

    client_request.post(
        "main.make_service_live",
        service_id=SERVICE_ONE_ID,
        _data={
            "enabled": post_data,
        },
        _expected_redirect=url_for("main.organisation_dashboard", org_id=ORGANISATION_ID),
    )

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        **expected_arguments_to_update_service,
    )


def test_post_make_service_live_page_error(
    mocker,
    client_request,
    platform_admin_user,
    service_one,
    mock_get_organisation,
    mock_update_service,
):
    service_one["has_active_go_live_request"] = True
    service_one["organisation"] = ORGANISATION_ID

    client_request.login(platform_admin_user)

    page = client_request.post(
        "main.make_service_live",
        service_id=SERVICE_ONE_ID,
        _data={},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one(".govuk-error-message")) == "Error: Select approve or reject"
    assert mock_update_service.called is False


@pytest.mark.parametrize(
    "post_data, expected_banner_class, expected_flash_message",
    (
        (True, ".banner-default-with-tick", "‘service one’ is now live"),
        (False, ".banner-default", "Request to go live rejected"),
    ),
)
def test_post_make_service_live_page_has_flash_message_after_redirect(
    mocker,
    client_request,
    platform_admin_user,
    service_one,
    mock_get_organisation,
    mock_update_service,
    post_data,
    expected_banner_class,
    expected_flash_message,
):
    mocker.patch("app.organisations_client.get_services_and_usage", return_value={"services": [], "updated_at": None})
    service_one["has_active_go_live_request"] = True
    service_one["organisation"] = ORGANISATION_ID

    client_request.login(platform_admin_user)

    page = client_request.post(
        "main.make_service_live",
        service_id=SERVICE_ONE_ID,
        _data={
            "enabled": post_data,
        },
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select_one(expected_banner_class).text) == expected_flash_message


@pytest.mark.parametrize(*pytest_user_auth_combinations)
def test_get_org_member_make_service_live_start(
    mocker,
    client_request,
    service_one,
    organisation_one,
    user,
    organisation_can_approve_own_go_live_requests,
    service_has_active_go_live_request,
    expected_status,
):
    organisation_one["can_approve_own_go_live_requests"] = organisation_can_approve_own_go_live_requests

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    service_one["has_active_go_live_request"] = service_has_active_go_live_request
    service_one["organisation"] = ORGANISATION_ID
    service_one["volume_letter"] = None

    client_request.login(user)

    page = client_request.get(
        "main.org_member_make_service_live_start",
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_status,
    )

    if expected_status == 200:
        assert (
            normalize_spaces(page.select_one("main p")) == "Test User has requested for this service to be made live."
        )
        assert [normalize_spaces(li) for li in page.select_one("main ul").select("li")] == [
            "111,111 emails per year",
            "222,222 text messages per year",
            "No letters",
        ]

        button = page.select_one("a.govuk-button")
        assert button.text.strip() == "Continue"
        assert button.get("href") == f"/services/{SERVICE_ONE_ID}/make-service-live/service-name"


@pytest.mark.parametrize(*pytest_user_auth_combinations)
def test_get_org_member_make_service_live_service_name(
    mocker,
    client_request,
    service_one,
    organisation_one,
    user,
    organisation_can_approve_own_go_live_requests,
    service_has_active_go_live_request,
    expected_status,
):
    organisation_one["can_approve_own_go_live_requests"] = organisation_can_approve_own_go_live_requests

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    service_one["has_active_go_live_request"] = service_has_active_go_live_request
    service_one["organisation"] = ORGANISATION_ID
    service_one["volume_letter"] = None

    client_request.login(user)

    page = client_request.get(
        "main.org_member_make_service_live_service_name",
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_status,
    )

    if expected_status == 200:
        assert f"The service name is: {service_one['name']}" in normalize_spaces(page.select_one("main").text)

        form = page.select_one("form")
        button = form.select_one("button")
        assert button.text.strip() == "Continue"


def test_post_org_member_make_service_live_service_name_error_summary(
    mocker,
    client_request,
    service_one,
    organisation_one,
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
        _expected_status=200,
        _data={},
    )

    error_summary = page.select_one(".govuk-error-summary")
    assert "There is a problem" in error_summary.text
    assert "Select yes or no" in error_summary.text


@pytest.mark.parametrize(
    "data, expected_redirect_url",
    (
        ({"enabled": True}, f"/services/{SERVICE_ONE_ID}/make-service-live/duplicate-service?name=ok"),
        ({"enabled": False}, f"/services/{SERVICE_ONE_ID}/make-service-live/duplicate-service?name=bad"),
    ),
)
def test_post_org_member_make_service_live_service_name(
    mocker, client_request, service_one, organisation_one, data, expected_redirect_url
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

    client_request.post(
        "main.org_member_make_service_live_service_name",
        service_id=SERVICE_ONE_ID,
        _expected_redirect=expected_redirect_url,
        _data=data,
    )


@pytest.mark.parametrize(*pytest_user_auth_combinations)
def test_get_org_member_make_service_live_duplicate_service(
    mocker,
    client_request,
    service_one,
    organisation_one,
    user,
    organisation_can_approve_own_go_live_requests,
    service_has_active_go_live_request,
    expected_status,
):
    organisation_one["can_approve_own_go_live_requests"] = organisation_can_approve_own_go_live_requests

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    service_one["has_active_go_live_request"] = service_has_active_go_live_request
    service_one["organisation"] = ORGANISATION_ID
    service_one["volume_letter"] = None

    client_request.login(user)

    page = client_request.get(
        "main.org_member_make_service_live_duplicate_service",
        service_id=SERVICE_ONE_ID,
        _expected_status=expected_status,
    )

    if expected_status == 200:
        assert "Duplicate service" in normalize_spaces(page.select_one("main").text)

        form = page.select_one("form")
        button = form.select_one("button")
        assert button.text.strip() == "Continue"


def test_post_org_member_make_service_live_duplicate_service_error_summary(
    mocker,
    client_request,
    service_one,
    organisation_one,
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
        "main.org_member_make_service_live_duplicate_service",
        service_id=SERVICE_ONE_ID,
        _expected_status=200,
        _data={},
    )

    error_summary = page.select_one(".govuk-error-summary")
    assert "There is a problem" in error_summary.text
    assert "Select yes or no" in error_summary.text


@pytest.mark.parametrize(
    "request_url, data, expected_redirect_url",
    (
        (
            f"/services/{SERVICE_ONE_ID}/make-service-live/duplicate-service?name=ok",
            {"enabled": True},
            f"/services/{SERVICE_ONE_ID}/make-service-live/contact-user?name=ok&duplicate=yes",
        ),
        (
            f"/services/{SERVICE_ONE_ID}/make-service-live/duplicate-service?name=ok",
            {"enabled": False},
            f"/services/{SERVICE_ONE_ID}/make-service-live/decision?name=ok&duplicate=no",
        ),
        (
            f"/services/{SERVICE_ONE_ID}/make-service-live/duplicate-service?name=bad",
            {"enabled": True},
            f"/services/{SERVICE_ONE_ID}/make-service-live/contact-user?name=bad&duplicate=yes",
        ),
        (
            f"/services/{SERVICE_ONE_ID}/make-service-live/duplicate-service?name=bad",
            {"enabled": False},
            f"/services/{SERVICE_ONE_ID}/make-service-live/contact-user?name=bad&duplicate=no",
        ),
    ),
)
def test_post_org_member_make_service_live_duplicate_service(
    mocker, client_request, service_one, organisation_one, request_url, data, expected_redirect_url
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


@pytest.mark.parametrize(
    "name, duplicate, expected_redirect",
    (
        ("ok", "no", f"/services/{SERVICE_ONE_ID}/make-service-live/decision"),
        ("bad", "no", None),
        ("ok", "yes", None),
        ("bad", "yes", None),
    ),
)
@pytest.mark.parametrize(*pytest_user_auth_combinations)
def test_get_org_member_make_service_live_contact_user(
    mocker,
    client_request,
    service_one,
    organisation_one,
    user,
    organisation_can_approve_own_go_live_requests,
    service_has_active_go_live_request,
    expected_status,
    name,
    duplicate,
    expected_redirect,
):
    organisation_one["can_approve_own_go_live_requests"] = organisation_can_approve_own_go_live_requests

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    service_one["has_active_go_live_request"] = service_has_active_go_live_request
    service_one["organisation"] = ORGANISATION_ID
    service_one["volume_letter"] = None

    client_request.login(user)

    page = client_request.get(
        "main.org_member_make_service_live_contact_user",
        service_id=SERVICE_ONE_ID,
        name=name,
        duplicate=duplicate,
        _expected_redirect=expected_redirect if expected_status == 200 else None,
        _expected_status=expected_status,
    )

    if expected_status == 200 and not expected_redirect:
        assert "Contact Test User" in normalize_spaces(page.select_one("main").text)

        finish = page.select_one("main a")
        assert finish.text.strip() == "Finish"
        assert finish.get("href") == f"/organisations/{ORGANISATION_ID}"


@pytest.mark.parametrize(*pytest_user_auth_combinations)
def test_get_org_member_make_service_live_decision(
    mocker,
    client_request,
    service_one,
    organisation_one,
    user,
    organisation_can_approve_own_go_live_requests,
    service_has_active_go_live_request,
    expected_status,
):
    organisation_one["can_approve_own_go_live_requests"] = organisation_can_approve_own_go_live_requests

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    service_one["has_active_go_live_request"] = service_has_active_go_live_request
    service_one["organisation"] = ORGANISATION_ID
    service_one["volume_letter"] = None

    client_request.login(user)

    page = client_request.get(
        "main.org_member_make_service_live_decision",
        service_id=SERVICE_ONE_ID,
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


def test_post_org_member_make_service_live_decision_error_summary(
    mocker,
    client_request,
    service_one,
    organisation_one,
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
        _expected_status=200,
        _data={},
    )

    error_summary = page.select_one(".govuk-error-summary")
    assert "There is a problem" in error_summary.text
    assert "Select approve or reject" in error_summary.text


@pytest.mark.parametrize(
    "post_data, expected_arguments_to_update_service",
    (
        (
            True,
            {
                "email_message_limit": 250_000,
                "sms_message_limit": 250_000,
                "letter_message_limit": 20_000,
                "restricted": False,
                "go_live_at": "2022-12-22 12:12:12",
                "has_active_go_live_request": False,
            },
        ),
        (
            False,
            {
                "email_message_limit": 50,
                "sms_message_limit": 50,
                "letter_message_limit": 50,
                "restricted": True,
                "go_live_at": None,
                "has_active_go_live_request": False,
            },
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
    post_data,
    expected_arguments_to_update_service,
):
    service_one["has_active_go_live_request"] = True
    service_one["organisation"] = ORGANISATION_ID

    client_request.login(platform_admin_user)

    client_request.post(
        "main.org_member_make_service_live_decision",
        service_id=SERVICE_ONE_ID,
        _data={
            "enabled": post_data,
        },
        _expected_redirect=url_for("main.organisation_dashboard", org_id=ORGANISATION_ID),
    )

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        **expected_arguments_to_update_service,
    )

from datetime import datetime
from unittest.mock import ANY, Mock, PropertyMock, call
from uuid import uuid4

import pytest
import pytz
from flask import url_for
from freezegun import freeze_time
from notifications_python_client.errors import HTTPError
from notifications_utils.clients.zendesk.zendesk_client import NotifySupportTicket, NotifyTicketType

from tests import invite_json, organisation_json, validate_route_permission
from tests.conftest import ORGANISATION_ID, SERVICE_ONE_ID, create_template, normalize_spaces


@pytest.mark.parametrize(
    "route",
    [
        "main.request_to_go_live",
        "main.submit_request_to_go_live",
    ],
)
def test_route_permissions(
    notify_admin,
    client_request,
    api_user_active,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_invites_for_service,
    single_sms_sender,
    route,
    mock_get_service_settings_page_common,
    mock_get_service_templates,
    mocker,
):
    validate_route_permission(
        mocker,
        notify_admin,
        "GET",
        200,
        url_for(route, service_id=service_one["id"]),
        ["manage_service"],
        api_user_active,
        service_one,
        session={"service_name_change": "New Service Name"},
    )


@pytest.mark.parametrize(
    "route",
    [
        "main.request_to_go_live",
        "main.submit_request_to_go_live",
    ],
)
def test_route_invalid_permissions(
    notify_admin,
    client_request,
    api_user_active,
    service_one,
    route,
    mock_get_service_templates,
    mock_get_invites_for_service,
    mocker,
):
    validate_route_permission(
        mocker,
        notify_admin,
        "GET",
        403,
        url_for(route, service_id=service_one["id"]),
        ["blah"],
        api_user_active,
        service_one,
    )


@pytest.mark.parametrize(
    "route",
    [
        "main.request_to_go_live",
        "main.submit_request_to_go_live",
    ],
)
def test_route_for_platform_admin(
    notify_admin,
    client_request,
    platform_admin_user,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    single_sms_sender,
    route,
    mock_get_service_settings_page_common,
    mock_get_service_templates,
    mock_get_invites_for_service,
    mocker,
):
    validate_route_permission(
        mocker,
        notify_admin,
        "GET",
        200,
        url_for(route, service_id=service_one["id"]),
        [],
        platform_admin_user,
        service_one,
        session={"service_name_change": "New Service Name"},
    )


@pytest.mark.parametrize(
    "confirmed_unique, expected_status_text",
    [
        (False, "Confirm that your service is unique Not completed"),
        (True, "Confirm that your service is unique Completed"),
    ],
)
def test_should_check_confirm_service_is_unique_task(
    client_request,
    service_one,
    single_sms_sender,
    single_reply_to_email_address,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    confirmed_unique,
    expected_status_text,
):
    service_one["confirmed_unique"] = confirmed_unique

    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Make your service live"

    assert normalize_spaces(page.select(".govuk-task-list .govuk-task-list__item")[0].text) == expected_status_text


@pytest.mark.parametrize(
    "volumes, expected_estimated_volumes_item",
    [
        ((0, 0, 0), "Tell us how many messages you expect to send Not completed"),
        ((1, 0, 0), "Tell us how many messages you expect to send Completed"),
        ((9, 99, 999), "Tell us how many messages you expect to send Completed"),
    ],
)
def test_should_check_if_estimated_volumes_provided(
    client_request,
    mocker,
    single_sms_sender,
    single_reply_to_email_address,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_get_organisation,
    mock_get_invites_for_service,
    volumes,
    expected_estimated_volumes_item,
):
    for volume, channel in zip(volumes, ("sms", "email", "letter"), strict=True):
        mocker.patch(
            f"app.models.service.Service.volume_{channel}",
            create=True,
            new_callable=PropertyMock,
            return_value=volume,
        )

    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Make your service live"

    assert (
        normalize_spaces(page.select(".govuk-task-list .govuk-task-list__item")[1].text)
        == expected_estimated_volumes_item
    )


@pytest.mark.parametrize(
    "volume_email,count_of_email_templates,reply_to_email_addresses,expected_reply_to_checklist_item",
    [
        pytest.param(None, 0, [], "", marks=pytest.mark.xfail(raises=IndexError)),
        pytest.param(0, 0, [], "", marks=pytest.mark.xfail(raises=IndexError)),
        (None, 1, [], "Add a reply-to email address Not completed"),
        (None, 1, [{}], "Add a reply-to email address Completed"),
        (1, 1, [], "Add a reply-to email address Not completed"),
        (1, 1, [{}], "Add a reply-to email address Completed"),
        (1, 0, [], "Add a reply-to email address Not completed"),
        (1, 0, [{}], "Add a reply-to email address Completed"),
    ],
)
def test_should_check_for_reply_to_on_go_live(
    client_request,
    mocker,
    service_one,
    single_sms_sender,
    volume_email,
    count_of_email_templates,
    reply_to_email_addresses,
    expected_reply_to_checklist_item,
    mock_get_invites_for_service,
    mock_get_users_by_service,
):
    mocker.patch(
        "app.service_api_client.get_service_templates",
        return_value={"data": [create_template(template_type="email") for _ in range(count_of_email_templates)]},
    )

    mock_get_reply_to_email_addresses = mocker.patch(
        "app.service_api_client.get_reply_to_email_addresses",
        return_value=reply_to_email_addresses,
    )

    for channel, volume in (("email", volume_email), ("sms", 0), ("letter", 1)):
        mocker.patch(
            f"app.models.service.Service.volume_{channel}",
            create=True,
            new_callable=PropertyMock,
            return_value=volume,
        )

    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Make your service live"

    checklist_items = page.select(".govuk-task-list .govuk-task-list__item")
    assert normalize_spaces(checklist_items[4].text) == expected_reply_to_checklist_item

    if count_of_email_templates:
        mock_get_reply_to_email_addresses.assert_called_once_with(SERVICE_ONE_ID)


@pytest.mark.parametrize(
    "count_of_users_with_manage_service,count_of_invites_with_manage_service,expected_user_checklist_item",
    [
        (1, 0, "Give another team member the ‘manage settings’ permission Not completed"),
        (2, 0, "Give another team member the ‘manage settings’ permission Completed"),
        (1, 1, "Give another team member the ‘manage settings’ permission Completed"),
    ],
)
@pytest.mark.parametrize(
    "count_of_templates, expected_templates_checklist_item",
    [
        (0, "Add templates with examples of your content Not completed"),
        (1, "Add templates with examples of your content Completed"),
        (2, "Add templates with examples of your content Completed"),
    ],
)
def test_should_check_for_sending_things_right(
    client_request,
    mocker,
    service_one,
    single_sms_sender,
    count_of_users_with_manage_service,
    count_of_invites_with_manage_service,
    expected_user_checklist_item,
    count_of_templates,
    expected_templates_checklist_item,
    active_user_with_permissions,
    active_user_no_settings_permission,
    single_reply_to_email_address,
):
    mocker.patch(
        "app.service_api_client.get_service_templates",
        return_value={"data": [create_template(template_type="sms") for _ in range(count_of_templates)]},
    )

    mock_get_users = mocker.patch(
        "app.models.user.Users._get_items",
        return_value=(
            [active_user_with_permissions] * count_of_users_with_manage_service + [active_user_no_settings_permission]
        ),
    )
    invite_one = invite_json(
        id_=uuid4(),
        from_user=service_one["users"][0],
        service_id=service_one["id"],
        email_address="invited_user@test.gov.uk",
        permissions="view_activity,send_messages,manage_service,manage_api_keys",
        created_at=datetime.utcnow(),
        status="pending",
        auth_type="sms_auth",
        folder_permissions=[],
    )

    invite_two = invite_one.copy()
    invite_two["permissions"] = "view_activity"

    mock_get_invites = mocker.patch(
        "app.models.user.InvitedUsers._get_items",
        return_value=(([invite_one] * count_of_invites_with_manage_service) + [invite_two]),
    )

    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Make your service live"

    checklist_items = page.select(".govuk-task-list .govuk-task-list__item")
    assert normalize_spaces(checklist_items[2].text) == expected_user_checklist_item
    assert normalize_spaces(checklist_items[3].text) == expected_templates_checklist_item

    mock_get_users.assert_called_once_with(SERVICE_ONE_ID)
    mock_get_invites.assert_called_once_with(SERVICE_ONE_ID)


@pytest.mark.parametrize(
    "checklist_completed, agreement_signed, disabled_button",
    (
        (True, True, False),
        (True, None, False),
        (True, False, True),
        (False, True, True),
        (False, None, True),
    ),
)
def test_should_show_disabled_go_live_button_if_checklist_not_complete(
    client_request,
    mocker,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_get_service_organisation,
    mock_get_invites_for_service,
    single_sms_sender,
    checklist_completed,
    agreement_signed,
    disabled_button,
):
    mocker.patch(
        "app.models.service.Service.go_live_checklist_completed",
        new_callable=PropertyMock,
        return_value=checklist_completed,
    )
    mocker.patch(
        "app.models.organisation.Organisation.agreement_signed",
        new_callable=PropertyMock,
        return_value=agreement_signed,
        create=True,
    )

    for channel in ("email", "sms", "letter"):
        mocker.patch(
            f"app.models.service.Service.volume_{channel}",
            create=True,
            new_callable=PropertyMock,
            return_value=0,
        )

    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Make your service live"
    assert page.select_one("form")["method"] == "post"
    assert page.select_one("form button").text.strip() == "Send a request to go live"

    if disabled_button:
        assert normalize_spaces(page.select_one("main p:last-of-type").text) == (
            "You must complete all the tasks before you can send a request to go live."
        )
        assert len(page.select_one("form button[disabled]")) == 1
    else:
        assert not any(
            p.text == "You must complete all the tasks before you can send a request to go live."
            for p in page.select("main p")
        )
        assert not (page.select_one("form button[disabled]"))


@pytest.mark.parametrize(
    "has_active_go_live_request, expected_button",
    (
        (True, False),
        (False, True),
    ),
)
def test_should_not_show_go_live_button_if_service_already_has_go_live_request(
    client_request,
    mocker,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_get_service_organisation,
    mock_get_invites_for_service,
    single_sms_sender,
    has_active_go_live_request,
    expected_button,
):
    mocker.patch(
        "app.models.service.Service.has_active_go_live_request",
        new_callable=PropertyMock,
        return_value=has_active_go_live_request,
        create=True,
    )
    mocker.patch(
        "app.models.service.Service.go_live_checklist_completed",
        new_callable=PropertyMock,
        return_value=True,
    )
    mocker.patch(
        "app.models.organisation.Organisation.agreement_signed",
        new_callable=PropertyMock,
        return_value=True,
        create=True,
    )

    for channel in ("email", "sms", "letter"):
        mocker.patch(
            f"app.models.service.Service.volume_{channel}",
            create=True,
            new_callable=PropertyMock,
            return_value=0,
        )

    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Make your service live"

    if expected_button:
        assert page.select_one("form button").text.strip() == "Send a request to go live"
    else:
        assert not page.select("form")
        assert not page.select("form button")
        assert len(page.select("main p")) == 2
        assert normalize_spaces(page.select_one("main p").text) == ("You sent a request to go live for this service.")


@pytest.mark.parametrize(
    "go_live_at, message",
    [
        (None, "‘service one’ is already live."),
        ("2020-10-09 13:55:20", "‘service one’ went live on 9 October 2020."),
    ],
)
def test_request_to_go_live_redirects_if_service_already_live(
    client_request,
    service_one,
    go_live_at,
    message,
):
    service_one["restricted"] = False
    service_one["go_live_at"] = go_live_at

    page = client_request.get(
        "main.request_to_go_live",
        service_id=SERVICE_ONE_ID,
    )

    assert page.select_one("h1").text == "Your service is already live"
    assert normalize_spaces(page.select_one("main p").text) == message


@pytest.mark.parametrize(
    "estimated_sms_volume,organisation_type,count_of_sms_templates,sms_senders,expected_sms_sender_checklist_item",
    [
        pytest.param(0, "local", 0, [], "", marks=pytest.mark.xfail(raises=IndexError)),
        pytest.param(
            None,
            "local",
            0,
            [{"is_default": True, "sms_sender": "GOVUK"}],
            "",
            marks=pytest.mark.xfail(raises=IndexError),
        ),
        pytest.param(
            1,
            "central",
            99,
            [{"is_default": True, "sms_sender": "GOVUK"}],
            "",
            marks=pytest.mark.xfail(raises=IndexError),
        ),
        pytest.param(
            None,
            "central",
            99,
            [{"is_default": True, "sms_sender": "GOVUK"}],
            "",
            marks=pytest.mark.xfail(raises=IndexError),
        ),
        pytest.param(
            1,
            "central",
            99,
            [{"is_default": True, "sms_sender": "GOVUK"}],
            "",
            marks=pytest.mark.xfail(raises=IndexError),
        ),
        (
            None,
            "local",
            1,
            [],
            "Change your Text message sender ID Not completed",
        ),
        (
            1,
            "nhs_local",
            0,
            [],
            "Change your Text message sender ID Not completed",
        ),
        (
            None,
            "school_or_college",
            1,
            [{"is_default": True, "sms_sender": "GOVUK"}],
            "Change your Text message sender ID Not completed",
        ),
        (
            None,
            "local",
            1,
            [
                {"is_default": False, "sms_sender": "GOVUK"},
                {"is_default": True, "sms_sender": "KUVOG"},
            ],
            "Change your Text message sender ID Completed",
        ),
        (
            None,
            "nhs_local",
            1,
            [{"is_default": True, "sms_sender": "KUVOG"}],
            "Change your Text message sender ID Completed",
        ),
    ],
)
def test_should_check_for_sms_sender_on_go_live(
    client_request,
    service_one,
    mocker,
    organisation_type,
    count_of_sms_templates,
    sms_senders,
    expected_sms_sender_checklist_item,
    estimated_sms_volume,
):
    service_one["organisation_type"] = organisation_type

    mocker.patch(
        "app.service_api_client.get_service_templates",
        return_value={"data": [create_template(template_type="sms") for _ in range(count_of_sms_templates)]},
    )

    mocker.patch(
        "app.models.service.Service.has_team_members_with_manage_service_permission",
        return_value=True,
    )

    mock_get_sms_senders = mocker.patch(
        "app.service_api_client.get_sms_senders",
        return_value=sms_senders,
    )

    for channel, volume in (("email", 0), ("sms", estimated_sms_volume)):
        mocker.patch(
            f"app.models.service.Service.volume_{channel}",
            create=True,
            new_callable=PropertyMock,
            return_value=volume,
        )

    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Make your service live"

    checklist_items = page.select(".govuk-task-list .govuk-task-list__item")
    assert normalize_spaces(checklist_items[4].text) == expected_sms_sender_checklist_item

    mock_get_sms_senders.assert_called_once_with(SERVICE_ONE_ID)


@pytest.mark.parametrize(
    "agreement_signed, expected_item",
    (
        pytest.param(None, "", marks=pytest.mark.xfail(raises=IndexError)),
        (
            True,
            "Accept our data processing and financial agreement Completed",
        ),
        (
            False,
            "Accept our data processing and financial agreement Not completed",
        ),
    ),
)
def test_should_check_for_mou_on_request_to_go_live(
    client_request,
    service_one,
    mocker,
    agreement_signed,
    mock_get_service_organisation,
    expected_item,
):
    mocker.patch(
        "app.models.service.Service.has_team_members_with_manage_service_permission",
        return_value=False,
    )
    mocker.patch(
        "app.models.service.Service.all_templates",
        new_callable=PropertyMock,
        return_value=[],
    )
    mocker.patch(
        "app.service_api_client.get_sms_senders",
        return_value=[],
    )
    mocker.patch(
        "app.service_api_client.get_reply_to_email_addresses",
        return_value=[],
    )
    for channel in {"email", "sms", "letter"}:
        mocker.patch(
            f"app.models.service.Service.volume_{channel}",
            create=True,
            new_callable=PropertyMock,
            return_value=None,
        )

    mocker.patch(
        "app.organisations_client.get_organisation", return_value=organisation_json(agreement_signed=agreement_signed)
    )
    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Make your service live"

    checklist_items = page.select(".govuk-task-list .govuk-task-list__item")
    assert normalize_spaces(checklist_items[4].text) == expected_item


def test_gp_without_organisation_is_shown_agreement_step(
    client_request,
    service_one,
    mocker,
):
    mocker.patch(
        "app.models.service.Service.has_team_members_with_manage_service_permission",
        return_value=False,
    )
    mocker.patch(
        "app.models.service.Service.all_templates",
        new_callable=PropertyMock,
        return_value=[],
    )
    mocker.patch(
        "app.service_api_client.get_sms_senders",
        return_value=[],
    )
    mocker.patch(
        "app.service_api_client.get_reply_to_email_addresses",
        return_value=[],
    )
    for channel in {"email", "sms", "letter"}:
        mocker.patch(
            f"app.models.service.Service.volume_{channel}",
            create=True,
            new_callable=PropertyMock,
            return_value=None,
        )
    mocker.patch(
        "app.models.service.Service.organisation_id",
        new_callable=PropertyMock,
        return_value=None,
    )
    mocker.patch(
        "app.models.service.Service.organisation_type",
        new_callable=PropertyMock,
        return_value="nhs_gp",
    )

    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Make your service live"
    assert normalize_spaces(
        page.select_one(".govuk-task-list:nth-of-type(2) .govuk-task-list__item:last-of-type").text
    ) == ("Accept our data processing and financial agreement Not completed")


def test_service_without_organisation_is_shown_agreement_text(
    client_request,
    service_one,
    mocker,
):
    mocker.patch(
        "app.models.service.Service.has_team_members_with_manage_service_permission",
        return_value=False,
    )
    mocker.patch(
        "app.models.service.Service.all_templates",
        new_callable=PropertyMock,
        return_value=[],
    )
    mocker.patch(
        "app.service_api_client.get_sms_senders",
        return_value=[],
    )
    mocker.patch(
        "app.service_api_client.get_reply_to_email_addresses",
        return_value=[],
    )
    for channel in {"email", "sms", "letter"}:
        mocker.patch(
            f"app.models.service.Service.volume_{channel}",
            create=True,
            new_callable=PropertyMock,
            return_value=None,
        )
    mocker.patch(
        "app.models.service.Service.organisation_id",
        new_callable=PropertyMock,
        return_value=None,
    )
    mocker.patch(
        "app.models.service.Service.organisation_type",
        new_callable=PropertyMock,
        return_value=None,
    )

    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Make your service live"
    assert normalize_spaces(page.select_one(".govuk-heading-m:last-of-type + p").text) == (
        "When you send us a request to go live, "
        "we’ll ask you the name of the public sector body responsible for your service."
    )


def test_service_where_organisation_has_agreement_accepted(
    client_request,
    mocker,
    service_one,
    mock_get_service_organisation,
):
    service_one["able_to_accept_agreement"] = False

    mocker.patch(
        "app.service_api_client.get_service_templates",
        return_value={"data": [create_template(template_type="sms")]},
    )

    mocker.patch(
        "app.models.service.Service.has_team_members_with_manage_service_permission",
        return_value=True,
    )

    mocker.patch(
        "app.service_api_client.get_sms_senders",
        return_value=[],
    )

    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            ORGANISATION_ID,
            "Org 1",
            agreement_signed=None,
        ),
    )
    for channel in ("email", "sms", "letter"):
        mocker.patch(
            f"app.models.service.Service.volume_{channel}",
            create=True,
            new_callable=PropertyMock,
            return_value=0,
        )

    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)

    assert (
        normalize_spaces(page.select_one(".govuk-heading-m:last-of-type ~ p").text)
        == "Org 1 has already accepted our data processing and financial agreement."
    )


def test_service_where_organisation_has_agreement_accepted_by_same_user(
    client_request,
    mocker,
    fake_uuid,
    service_one,
    mock_get_service_organisation,
):
    mocker.patch(
        "app.service_api_client.get_service_templates",
        return_value={"data": [create_template(template_type="sms")]},
    )

    mocker.patch(
        "app.models.service.Service.has_team_members_with_manage_service_permission",
        return_value=True,
    )

    mocker.patch(
        "app.service_api_client.get_sms_senders",
        return_value=[],
    )

    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            ORGANISATION_ID,
            "Org 1",
            agreement_signed=True,
            agreement_signed_by_id=fake_uuid,
        ),
    )
    for channel in ("email", "sms", "letter"):
        mocker.patch(
            f"app.models.service.Service.volume_{channel}",
            create=True,
            new_callable=PropertyMock,
            return_value=0,
        )

    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)

    assert normalize_spaces(
        page.select_one(".govuk-task-list:nth-of-type(2) .govuk-task-list__item:last-of-type").text
    ) == ("Accept our data processing and financial agreement Completed")


def test_non_gov_user_is_told_they_cant_go_live(
    client_request,
    api_nongov_user_active,
    mocker,
    mock_get_organisations,
    mock_get_organisation,
):
    mocker.patch(
        "app.models.service.Service.has_team_members_with_manage_service_permission",
        return_value=False,
    )
    mocker.patch(
        "app.models.service.Service.all_templates",
        new_callable=PropertyMock,
        return_value=[],
    )
    mocker.patch(
        "app.service_api_client.get_sms_senders",
        return_value=[],
    )
    mocker.patch(
        "app.service_api_client.get_reply_to_email_addresses",
        return_value=[],
    )
    client_request.login(api_nongov_user_active)
    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)
    assert normalize_spaces(page.select_one("main p:last-of-type").text) == (
        "Only team members with a government email address can request to go live."
    )
    assert len(page.select("main form")) == 0
    assert len(page.select("main button")) == 0


def test_non_gov_users_cant_request_to_go_live(
    client_request,
    api_nongov_user_active,
    mock_get_organisations,
):
    client_request.login(api_nongov_user_active)
    client_request.post(
        "main.request_to_go_live",
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
    )


@freeze_time("2012-12-21 13:12:12.12354")
def test_should_render_the_same_page_after_request_to_go_live(
    client_request,
    mocker,
    active_user_with_permissions,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisations_and_services_for_user,
    single_sms_sender,
    mock_get_service_organisation,
    mock_get_service_settings_page_common,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_update_service,
    mock_get_invites_without_manage_permission,
    mock_notify_users_of_request_to_go_live_for_service,
):
    service_one["go_live_user"] = active_user_with_permissions["id"]
    service_one["has_active_go_live_request"] = True
    mocker.patch(
        "app.models.service.Service.go_live_checklist_completed",
        new_callable=PropertyMock,
        return_value=True,
    )

    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            ORGANISATION_ID,
            "Org 1",
            agreement_signed=True,
        ),
    )
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mock_send_ticket_to_zendesk = mocker.patch(
        "app.main.views.make_your_service_live.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )
    page = client_request.post("main.request_to_go_live", service_id=SERVICE_ONE_ID, _follow_redirects=True)

    expected_message = (
        "Service: service one\n"
        "http://localhost/services/{service_id}\n"
        "\n"
        "---\n"
        "Organisation type: Central government\n"
        "Agreement signed: Yes, for Org 1.\n"
        "\n"
        "Other live services for that user: No\n"
        "\n"
        "---\n"
        "Request sent by test@user.gov.uk\n"
        "Requester’s user page: http://localhost/users/{user_id}\n"
    ).format(
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
    )

    mock_create_ticket.assert_called_once_with(
        ANY,
        subject="Request to go live - service one",
        message=expected_message,
        ticket_type="task",
        notify_ticket_type=NotifyTicketType.NON_TECHNICAL,
        user_name=active_user_with_permissions["name"],
        user_email=active_user_with_permissions["email_address"],
        requester_sees_message_content=False,
        org_id=ORGANISATION_ID,
        org_type="central",
        service_id=SERVICE_ONE_ID,
        notify_task_type="notify_task_go_live_request",
        user_created_at=datetime(2018, 11, 7, 8, 34, 54, 857402).replace(tzinfo=pytz.utc),
    )
    mock_send_ticket_to_zendesk.assert_called_once()

    assert normalize_spaces(page.select_one(".banner-default").text) == (
        "Thanks for your request to go live. We’ll get back to you within one working day."
    )
    assert normalize_spaces(page.select_one("main p").text) == ("You sent a request to go live for this service.")
    assert normalize_spaces(page.select_one("h1").text) == "Make your service live"

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        go_live_user=active_user_with_permissions["id"],
        has_active_go_live_request=True,
    )


def test_should_not_submit_the_form_if_not_all_tasks_completed(
    client_request,
    mocker,
    active_user_with_permissions,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisations_and_services_for_user,
    single_sms_sender,
    mock_get_service_settings_page_common,
    mock_get_users_by_service,
    mock_update_service,
):
    mocker.patch(
        "app.models.service.Service.go_live_checklist_completed",
        new_callable=PropertyMock,
        return_value=False,
    )
    client_request.post(
        "main.request_to_go_live",
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
    )


@pytest.mark.parametrize(
    "can_approve_own_go_live_requests, expected_subject, expected_go_live_notes, expected_zendesk_task_type",
    (
        (
            False,
            "Request to go live - service one",
            "This service is not allowed to go live",
            "notify_task_go_live_request",
        ),
        (
            True,
            "Self approve go live request - service one",
            (
                "This organisation can approve its own go live requests. "
                "No action should be needed from us. "
                "This service is not allowed to go live"
            ),
            "notify_task_go_live_request_self_approve",
        ),
    ),
)
def test_request_to_go_live_displays_go_live_notes_in_zendesk_ticket(
    client_request,
    mocker,
    active_user_with_permissions,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisations_and_services_for_user,
    single_sms_sender,
    mock_get_service_organisation,
    mock_get_service_settings_page_common,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_update_service,
    mock_get_invites_without_manage_permission,
    mock_notify_users_of_request_to_go_live_for_service,
    can_approve_own_go_live_requests,
    expected_go_live_notes,
    expected_subject,
    expected_zendesk_task_type,
):
    mocker.patch(
        "app.models.service.Service.go_live_checklist_completed",
        new_callable=PropertyMock,
        return_value=True,
    )

    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            ORGANISATION_ID,
            "Org 1",
            agreement_signed=True,
            request_to_go_live_notes="This service is not allowed to go live",
            can_approve_own_go_live_requests=can_approve_own_go_live_requests,
        ),
    )
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mock_send_ticket_to_zendesk = mocker.patch(
        "app.main.views.make_your_service_live.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )
    client_request.post("main.request_to_go_live", service_id=SERVICE_ONE_ID, _follow_redirects=True)

    expected_message = (
        "Service: service one\n"
        "http://localhost/services/{service_id}\n"
        "\n"
        "---\n"
        "Organisation type: Central government\n"
        "Agreement signed: Yes, for Org 1. {expected_go_live_notes}\n"
        "\n"
        "Other live services for that user: No\n"
        "\n"
        "---\n"
        "Request sent by test@user.gov.uk\n"
        "Requester’s user page: http://localhost/users/{user_id}\n"
    ).format(
        service_id=SERVICE_ONE_ID,
        expected_go_live_notes=expected_go_live_notes,
        user_id=active_user_with_permissions["id"],
    )

    mock_create_ticket.assert_called_once_with(
        ANY,
        subject=expected_subject,
        message=expected_message,
        ticket_type="task",
        notify_ticket_type=NotifyTicketType.NON_TECHNICAL,
        user_name=active_user_with_permissions["name"],
        user_email=active_user_with_permissions["email_address"],
        requester_sees_message_content=False,
        org_id=ORGANISATION_ID,
        org_type="central",
        service_id=SERVICE_ONE_ID,
        notify_task_type=expected_zendesk_task_type,
        user_created_at=datetime(2018, 11, 7, 8, 34, 54, 857402).replace(tzinfo=pytz.utc),
    )
    mock_send_ticket_to_zendesk.assert_called_once()


def test_request_to_go_live_displays_mou_signatories(
    client_request,
    mocker,
    fake_uuid,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisations_and_services_for_user,
    single_sms_sender,
    mock_get_service_organisation,
    mock_get_service_settings_page_common,
    mock_update_service,
    active_user_with_permissions,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_get_invites_without_manage_permission,
    mock_notify_users_of_request_to_go_live_for_service,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            ORGANISATION_ID,
            "Org 1",
            agreement_signed=True,
            agreement_signed_by_id=fake_uuid,
            agreement_signed_on_behalf_of_email_address="bigdog@example.gov.uk",
        ),
    )
    mocker.patch(
        "app.models.service.Service.go_live_checklist_completed",
        new_callable=PropertyMock,
        return_value=True,
    )
    mocker.patch(
        "app.main.views.make_your_service_live.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    client_request.post("main.request_to_go_live", service_id=SERVICE_ONE_ID, _follow_redirects=True)

    assert (
        "Organisation type: Central government\n"
        "Agreement signed: Yes, for Org 1.\n"
        "Agreement signed by: test@user.gov.uk\n"
        "Agreement signed on behalf of: bigdog@example.gov.uk\n"
    ) in mock_create_ticket.call_args[1]["message"]


def test_should_be_able_to_request_to_go_live_with_no_organisation(
    client_request,
    mocker,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisations_and_services_for_user,
    single_sms_sender,
    mock_get_service_settings_page_common,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_update_service,
    mock_get_invites_without_manage_permission,
):
    for channel in {"email", "sms", "letter"}:
        mocker.patch(
            f"app.models.service.Service.volume_{channel}",
            create=True,
            new_callable=PropertyMock,
            return_value=1,
        )
    mocker.patch(
        "app.models.service.Service.go_live_checklist_completed",
        new_callable=PropertyMock,
        return_value=True,
    )
    mock_post = mocker.patch(
        "app.main.views.make_your_service_live.zendesk_client.send_ticket_to_zendesk", autospec=True
    )

    client_request.post("main.request_to_go_live", service_id=SERVICE_ONE_ID, _follow_redirects=True)

    assert mock_post.called is True


@pytest.mark.parametrize(
    "can_approve_own_go_live_requests, expected_call_args",
    (
        (True, [call(SERVICE_ONE_ID)]),
        (False, []),
    ),
)
def test_request_to_go_live_is_sent_to_organiation_if_can_be_approved_by_organisation(
    client_request,
    mocker,
    mock_get_organisations_and_services_for_user,
    mock_get_service_organisation,
    mock_update_service,
    mock_notify_users_of_request_to_go_live_for_service,
    organisation_one,
    can_approve_own_go_live_requests,
    expected_call_args,
):
    organisation_one["can_approve_own_go_live_requests"] = can_approve_own_go_live_requests
    mocker.patch(
        "app.models.service.Service.go_live_checklist_completed",
        new_callable=PropertyMock,
        return_value=True,
    )
    mocker.patch(
        "app.models.organisation.Organisation.agreement_signed",
        new_callable=PropertyMock,
        return_value=True,
        create=True,
    )
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)
    mocker.patch("app.main.views.make_your_service_live.zendesk_client.send_ticket_to_zendesk", autospec=True)

    client_request.post("main.request_to_go_live", service_id=SERVICE_ONE_ID)

    assert mock_notify_users_of_request_to_go_live_for_service.call_args_list == expected_call_args


def test_confirm_service_is_unique_sets_confirmed_unique_and_updates_name(
    client_request,
    mock_update_service,
    service_one,
):
    client_request.post(
        "main.confirm_service_is_unique",
        service_id=SERVICE_ONE_ID,
        _data={"name": "Updated Service"},
        _expected_status=302,
        _expected_redirect=url_for("main.request_to_go_live", service_id=SERVICE_ONE_ID),
    )

    mock_update_service.assert_called_once_with(SERVICE_ONE_ID, name="Updated Service", confirmed_unique=True)


@pytest.mark.parametrize(
    "name, error_message",
    [
        ("", "Error: Enter a service name"),
        (".", "Service name must include at least 2 letters or numbers"),
        ("GOV.UK Ειδοποίηση", "Service name cannot include characters from a non-Latin alphabet"),
        ("a" * 150 + " " * 100 + "a", "Service name cannot be longer than 143 characters"),
    ],
)
def test_confirm_service_is_unique_fails_validation(
    client_request,
    mock_update_service,
    name,
    error_message,
):
    page = client_request.post(
        "main.confirm_service_is_unique",
        service_id=SERVICE_ONE_ID,
        _data={"name": name},
        _expected_status=200,
    )

    assert not mock_update_service.called
    assert error_message in page.select_one(".govuk-error-message").text


def test_confirm_service_is_unique_doesnt_suppress_api_errors(client_request, mocker, service_one):
    mocker.patch(
        "app.main.views.service_settings.index.service_api_client.update_service",
        side_effect=HTTPError(response=Mock(status_code=500)),
    )

    client_request.post(
        "main.confirm_service_is_unique",
        service_id=SERVICE_ONE_ID,
        _data={"name": "Whatever"},
        _expected_status=500,
    )


def test_confirm_service_is_unique_prefills_name(client_request, service_one):
    page = client_request.get(
        "main.confirm_service_is_unique",
        service_id=SERVICE_ONE_ID,
    )

    assert page.select_one("input[name=name]")["value"] == service_one["name"]

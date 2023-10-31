from datetime import datetime, timedelta
from unittest.mock import ANY

import pytest
from flask import url_for
from freezegun import freeze_time

from app.constants import PERMISSION_CAN_MAKE_SERVICES_LIVE
from app.models.user import InvitedOrgUser
from tests import organisation_json
from tests.conftest import ORGANISATION_ID, create_active_user_with_permissions, normalize_spaces


@pytest.mark.parametrize(
    "can_approve_own_go_live_requests, expected_radios",
    (
        (False, []),
        (True, [("can_make_services_live", "This team member can make new services live")]),
    ),
)
def test_invite_org_user_page(client_request, mocker, can_approve_own_go_live_requests, expected_radios):
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(
            ORGANISATION_ID,
            "Test organisation",
            can_approve_own_go_live_requests=can_approve_own_go_live_requests,
        ),
    )

    page = client_request.get(
        ".invite_org_user",
        org_id=ORGANISATION_ID,
    )

    assert [
        (
            checkbox.select_one("input")["value"],
            normalize_spaces(checkbox.select_one("label").text),
        )
        for checkbox in page.select(".govuk-checkboxes__item")
    ] == expected_radios


@pytest.mark.parametrize(
    "can_approve_own_go_live_requests, extra_form_data, expected_status",
    (
        (False, {}, 302),
        (False, {"permissions_field": ["can_make_services_live"]}, 200),
        (True, {}, 302),
        (True, {"permissions_field": ["can_make_services_live"]}, 302),
    ),
)
def test_invite_org_user(
    client_request, mocker, sample_org_invite, can_approve_own_go_live_requests, extra_form_data, expected_status
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(
            ORGANISATION_ID,
            "Test organisation",
            can_approve_own_go_live_requests=can_approve_own_go_live_requests,
        ),
    )

    mock_invite_org_user = mocker.patch(
        "app.org_invite_api_client.create_invite",
        return_value=sample_org_invite,
    )

    page = client_request.post(
        ".invite_org_user",
        org_id=ORGANISATION_ID,
        _data={"email_address": "test@example.gov.uk", **extra_form_data},
        _expected_status=expected_status,
    )

    # The page has been re-rendered with an error because the form submission is invalid
    if expected_status == 200:
        assert "'can_make_services_live' is not a valid choice for" in page.text
        assert mock_invite_org_user.call_args_list == []

    # The user has been redirected because the form submission was good
    else:
        assert mock_invite_org_user.call_args_list == [
            mocker.call(
                sample_org_invite["invited_by"],
                f"{ORGANISATION_ID}",
                "test@example.gov.uk",
                extra_form_data.get("permissions_field", []),
            )
        ]


def test_invite_org_user_errors_when_same_email_as_inviter(
    client_request,
    mocker,
    mock_get_organisation,
    sample_org_invite,
):
    new_org_user_data = {
        "email_address": "test@user.gov.uk",
    }

    mock_invite_org_user = mocker.patch(
        "app.org_invite_api_client.create_invite",
        return_value=sample_org_invite,
    )

    page = client_request.post(
        ".invite_org_user", org_id=ORGANISATION_ID, _data=new_org_user_data, _follow_redirects=True
    )

    assert mock_invite_org_user.called is False
    assert "Enter an email address that is not your own" in normalize_spaces(
        page.select_one(".govuk-error-message").text
    )


def test_cancel_invited_org_user_cancels_user_invitations(
    client_request,
    mock_get_invites_for_organisation,
    sample_org_invite,
    mock_get_organisation,
    mock_get_users_for_organisation,
    mocker,
):
    mock_cancel = mocker.patch("app.org_invite_api_client.cancel_invited_user")
    mocker.patch("app.org_invite_api_client.get_invited_user_for_org", return_value=sample_org_invite)

    page = client_request.get(
        "main.cancel_invited_org_user",
        org_id=ORGANISATION_ID,
        invited_user_id=sample_org_invite["id"],
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Team members"
    flash_banner = normalize_spaces(page.select_one("div.banner-default-with-tick").text)
    assert flash_banner == f"Invitation cancelled for {sample_org_invite['email_address']}"
    mock_cancel.assert_called_once_with(
        org_id=ORGANISATION_ID,
        invited_user_id=sample_org_invite["id"],
    )


def test_accepted_invite_when_other_user_already_logged_in(client_request, mock_check_org_invite_token):
    page = client_request.get(
        "main.accept_org_invite",
        token="thisisnotarealtoken",
        follow_redirects=True,
        _expected_status=403,
    )
    assert "This invite is for another email address." in normalize_spaces(page.select_one(".banner-dangerous").text)


def test_cancelled_invite_opened_by_user(
    mocker, client_request, api_user_active, mock_check_org_cancelled_invite_token, mock_get_organisation, fake_uuid
):
    client_request.logout()
    mock_get_user = mocker.patch("app.user_api_client.get_user", return_value=api_user_active)

    page = client_request.get(
        "main.accept_org_invite",
        token="thisisnotarealtoken",
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one("h1").text) == "The invitation you were sent has been cancelled"
    assert normalize_spaces(page.select("main p")[0].text) == "Test User decided to cancel this invitation."
    assert (
        normalize_spaces(page.select("main p")[1].text)
        == "If you need access to Test organisation, you’ll have to ask them to invite you again."
    )

    mock_get_user.assert_called_once_with(fake_uuid)
    mock_get_organisation.assert_called_once_with(ORGANISATION_ID)


def test_user_invite_already_accepted(client_request, mock_check_org_accepted_invite_token):
    client_request.logout()
    client_request.get(
        "main.accept_org_invite",
        token="thisisnotarealtoken",
        _expected_redirect=url_for(
            "main.organisation_dashboard",
            org_id=ORGANISATION_ID,
        ),
    )


@freeze_time("2021-12-12 12:12:12")
def test_existing_user_invite_already_is_member_of_organisation(
    client_request,
    mock_check_org_invite_token,
    mock_get_user,
    mock_get_user_by_email,
    api_user_active,
    mock_get_users_for_organisation,
    mock_accept_org_invite,
    mock_add_user_to_organisation,
    mock_update_user_attribute,
):
    client_request.logout()
    mock_update_user_attribute.reset_mock()
    client_request.get(
        "main.accept_org_invite",
        token="thisisnotarealtoken",
        _expected_redirect=url_for(
            "main.organisation_dashboard",
            org_id=ORGANISATION_ID,
        ),
    )

    mock_check_org_invite_token.assert_called_once_with("thisisnotarealtoken")
    mock_accept_org_invite.assert_called_once_with(ORGANISATION_ID, ANY)
    mock_get_user_by_email.assert_called_once_with("invited_user@test.gov.uk")
    mock_get_users_for_organisation.assert_called_once_with(ORGANISATION_ID)
    mock_update_user_attribute.assert_called_once_with(
        api_user_active["id"],
        email_access_validated_at="2021-12-12T12:12:12",
    )


@freeze_time("2021-12-12 12:12:12")
def test_existing_user_invite_not_a_member_of_organisation(
    client_request,
    api_user_active,
    mock_check_org_invite_token,
    mock_get_user_by_email,
    mock_get_users_for_organisation,
    mock_accept_org_invite,
    mock_add_user_to_organisation,
    mock_update_user_attribute,
):
    client_request.logout()
    mock_update_user_attribute.reset_mock()
    client_request.get(
        "main.accept_org_invite",
        token="thisisnotarealtoken",
        _expected_redirect=url_for(
            "main.organisation_dashboard",
            org_id=ORGANISATION_ID,
        ),
    )

    mock_check_org_invite_token.assert_called_once_with("thisisnotarealtoken")
    mock_accept_org_invite.assert_called_once_with(ORGANISATION_ID, ANY)
    mock_get_user_by_email.assert_called_once_with("invited_user@test.gov.uk")
    mock_get_users_for_organisation.assert_called_once_with(ORGANISATION_ID)
    mock_add_user_to_organisation.assert_called_once_with(
        ORGANISATION_ID,
        api_user_active["id"],
        permissions=[PERMISSION_CAN_MAKE_SERVICES_LIVE],
    )
    mock_update_user_attribute.assert_called_once_with(
        mock_get_user_by_email.side_effect(None)["id"],
        email_access_validated_at="2021-12-12T12:12:12",
    )


def test_user_accepts_invite(
    client_request,
    mock_check_org_invite_token,
    mock_dont_get_user_by_email,
    mock_get_users_for_organisation,
):
    client_request.logout()
    client_request.get(
        "main.accept_org_invite",
        token="thisisnotarealtoken",
        _expected_redirect=url_for("main.register_from_org_invite"),
    )

    mock_check_org_invite_token.assert_called_once_with("thisisnotarealtoken")
    mock_dont_get_user_by_email.assert_called_once_with("invited_user@test.gov.uk")
    mock_get_users_for_organisation.assert_called_once_with(ORGANISATION_ID)


def test_registration_from_org_invite_404s_if_user_not_in_session(
    client_request,
):
    client_request.logout()
    client_request.get(
        "main.register_from_org_invite",
        _expected_status=404,
    )


@pytest.mark.parametrize(
    "data, error",
    [
        [
            {"name": "Bad Mobile", "mobile_number": "not good", "password": "validPassword!"},
            "Mobile numbers can only include: 0 1 2 3 4 5 6 7 8 9 ( ) + -",
        ],
        [
            {"name": "Bad Password", "mobile_number": "+44123412345", "password": "password"},
            "Choose a password that’s harder to guess",
        ],
    ],
)
def test_registration_from_org_invite_has_bad_data(
    client_request,
    sample_org_invite,
    data,
    error,
    mock_get_invited_org_user_by_id,
):
    client_request.logout()

    with client_request.session_transaction() as session:
        session["invited_org_user_id"] = sample_org_invite["id"]

    page = client_request.post(
        "main.register_from_org_invite",
        _data=data,
        _expected_status=200,
    )

    assert error in page.text


@pytest.mark.parametrize("diff_data", [["email_address"], ["organisation"], ["email_address", "organisation"]])
def test_registration_from_org_invite_has_different_email_or_organisation(
    client_request,
    sample_org_invite,
    diff_data,
    mock_get_invited_org_user_by_id,
):
    client_request.logout()
    with client_request.session_transaction() as session:
        session["invited_org_user_id"] = sample_org_invite["id"]

    data = {
        "name": "Test User",
        "mobile_number": "+4407700900460",
        "password": "validPassword!",
        "email_address": sample_org_invite["email_address"],
        "organisation": sample_org_invite["organisation"],
    }
    for field in diff_data:
        data[field] = "different"

    client_request.post(
        "main.register_from_org_invite",
        _data=data,
        _expected_status=400,
    )


def test_org_user_registers_with_email_already_in_use(
    client_request,
    sample_org_invite,
    mock_get_user_by_email,
    mock_accept_org_invite,
    mock_add_user_to_organisation,
    mock_send_already_registered_email,
    mock_register_user,
    mock_get_invited_org_user_by_id,
):
    client_request.logout()
    with client_request.session_transaction() as session:
        session["invited_org_user_id"] = sample_org_invite["id"]

    client_request.post(
        "main.register_from_org_invite",
        _data={
            "name": "Test User",
            "mobile_number": "+4407700900460",
            "password": "validPassword!",
            "email_address": sample_org_invite["email_address"],
            "organisation": sample_org_invite["organisation"],
        },
        _expected_redirect=url_for("main.verify"),
    )

    mock_get_user_by_email.assert_called_once_with(sample_org_invite["email_address"])
    assert mock_register_user.called is False
    assert mock_send_already_registered_email.called is False


def test_org_user_registration(
    client_request,
    sample_org_invite,
    mock_email_is_not_already_in_use,
    mock_register_user,
    mock_send_verify_code,
    mock_get_user_by_email,
    mock_send_verify_email,
    mock_accept_org_invite,
    mock_add_user_to_organisation,
    mock_get_invited_org_user_by_id,
):
    client_request.logout()
    with client_request.session_transaction() as session:
        session["invited_org_user_id"] = sample_org_invite["id"]

    client_request.post(
        "main.register_from_org_invite",
        _data={
            "name": "Test User",
            "email_address": sample_org_invite["email_address"],
            "mobile_number": "+4407700900460",
            "password": "validPassword!",
            "organisation": sample_org_invite["organisation"],
        },
        _expected_redirect=url_for("main.verify"),
    )

    assert mock_get_user_by_email.called is False
    mock_register_user.assert_called_once_with(
        "Test User", sample_org_invite["email_address"], "+4407700900460", "validPassword!", "sms_auth"
    )
    mock_send_verify_code.assert_called_once_with(
        "6ce466d0-fd6a-11e5-82f5-e0accb9d11a6",
        "sms",
        "+4407700900460",
    )
    mock_get_invited_org_user_by_id.assert_called_once_with(sample_org_invite["id"])


def test_verified_org_user_redirects_to_dashboard(
    client_request,
    sample_org_invite,
    mock_check_verify_code,
    mock_get_user,
    mock_activate_user,
    mock_login,
):
    client_request.logout()
    invited_org_user = InvitedOrgUser(sample_org_invite)
    with client_request.session_transaction() as session:
        session["expiry_date"] = str(datetime.utcnow() + timedelta(hours=1))
        session["user_details"] = {"email": invited_org_user.email_address, "id": invited_org_user.id}
        session["organisation_id"] = invited_org_user.organisation

    client_request.post(
        "main.verify",
        _data={"sms_code": "12345"},
        _expected_redirect=url_for(
            "main.organisation_dashboard",
            org_id=invited_org_user.organisation,
        ),
    )


class TestEditOrganisationUser:
    @pytest.fixture
    def _other_user(self):
        return create_active_user_with_permissions(with_unique_id=True)

    @pytest.fixture
    def _get_user_fn(self, platform_admin_user, _other_user):
        def _get_user(user_id):
            if user_id == platform_admin_user["id"]:
                return platform_admin_user
            elif user_id == _other_user["id"]:
                return _other_user

            raise ValueError("unknown user id for mock")

        return _get_user

    def _mock_get_organistion_can_approve_go_live(self, mocker):
        def _get_organisation(org_id):
            return organisation_json(
                org_id,
                {
                    "o1": "Org 1",
                    "o2": "Org 2",
                    "o3": "Org 3",
                }.get(org_id, "Test organisation"),
                can_approve_own_go_live_requests=True,
            )

        return mocker.patch("app.organisations_client.get_organisation", side_effect=_get_organisation)

    def test_edit_organisation_user_shows_the_delete_confirmation_banner(
        self,
        client_request,
        mock_get_organisation,
        mock_get_invites_for_organisation,
        platform_admin_user,
        _other_user,
        _get_user_fn,
        mocker,
    ):
        mocker.patch("app.models.user.OrganisationUsers.client_method", return_value=[_other_user])
        client_request.login(platform_admin_user)

        # Override the `get_user` mock from `login` because we need to be able to get multiple users
        mocker.patch("app.user_api_client.get_user", side_effect=_get_user_fn)

        page = client_request.get(
            "main.edit_organisation_user", org_id=ORGANISATION_ID, user_id=_other_user["id"], delete="yes"
        )

        assert normalize_spaces(page.select_one("h1").text) == "Test User"

        banner = page.select_one(".banner-dangerous")
        assert "Are you sure you want to remove Test User?" in normalize_spaces(banner.contents[0])
        assert banner.form.attrs["action"] == url_for(
            "main.remove_user_from_organisation", org_id=ORGANISATION_ID, user_id=_other_user["id"]
        )

    def test_set_permissions(
        self,
        client_request,
        mock_get_invites_for_organisation,
        platform_admin_user,
        _other_user,
        _get_user_fn,
        mocker,
    ):
        self._mock_get_organistion_can_approve_go_live(mocker)
        mocker.patch("app.models.user.OrganisationUsers.client_method", return_value=[_other_user])
        mock_set_org_permissions = mocker.patch(
            "app.notify_client.user_api_client.UserApiClient.set_organisation_permissions"
        )
        mock_event = mocker.patch("app.models.user.create_set_organisation_user_permissions_event")
        client_request.login(platform_admin_user)

        # Override the `get_user` mock from `login` because we need to be able to get multiple users
        mocker.patch("app.user_api_client.get_user", side_effect=_get_user_fn)

        client_request.post(
            "main.edit_organisation_user",
            org_id=ORGANISATION_ID,
            user_id=_other_user["id"],
            _data={
                "permissions_field": [
                    PERMISSION_CAN_MAKE_SERVICES_LIVE,
                ],
            },
            _expected_redirect="",
        )

        assert mock_set_org_permissions.call_args_list == [
            mocker.call(
                _other_user["id"],
                organisation_id=ORGANISATION_ID,
                permissions=[{"permission": PERMISSION_CAN_MAKE_SERVICES_LIVE}],
            )
        ]
        assert mock_event.call_args_list == [
            mocker.call(
                user_id=_other_user["id"],
                organisation_id=ORGANISATION_ID,
                original_permissions=set(),
                new_permissions=[PERMISSION_CAN_MAKE_SERVICES_LIVE],
                set_by_id=platform_admin_user["id"],
            )
        ]

    def test_cannot_set_org_user_permissions_filtered_out_by_org_perms(
        self,
        client_request,
        mock_get_organisation,
        mock_get_invites_for_organisation,
        platform_admin_user,
        _other_user,
        _get_user_fn,
        mocker,
    ):
        mocker.patch("app.models.user.OrganisationUsers.client_method", return_value=[_other_user])
        mocker.patch("app.notify_client.user_api_client.UserApiClient.set_organisation_permissions")
        mocker.patch("app.models.user.create_set_organisation_user_permissions_event")
        client_request.login(platform_admin_user)

        # Override the `get_user` mock from `login` because we need to be able to get multiple users
        mocker.patch("app.user_api_client.get_user", side_effect=_get_user_fn)

        page = client_request.post(
            "main.edit_organisation_user",
            org_id=ORGANISATION_ID,
            user_id=_other_user["id"],
            _data={
                "permissions_field": [
                    PERMISSION_CAN_MAKE_SERVICES_LIVE,
                ],
            },
            _expected_status=200,
        )

        assert "Error: 'can_make_services_live' is not a valid choice for this field." in page.text

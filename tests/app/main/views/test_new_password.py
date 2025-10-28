import json
from datetime import UTC, datetime

import pytest
from flask import url_for
from freezegun import freeze_time
from itsdangerous import SignatureExpired
from notifications_utils.url_safe_token import generate_token

from tests.conftest import SERVICE_ONE_ID, url_for_endpoint_with_token


@freeze_time("2021-01-01 11:11:11")
def test_should_render_new_password_template(
    notify_admin,
    client_request,
    mock_get_user_by_email_request_password_reset,
    mocker,
):
    client_request.logout()
    user = mock_get_user_by_email_request_password_reset.return_value
    user["password_changed_at"] = "2021-01-01 00:00:00"
    mock_update_user_attribute = mocker.patch(
        "app.user_api_client.update_user_attribute",
        return_value=user,
    )
    data = json.dumps({"email": user["email_address"], "created_at": str(datetime.now(UTC))})
    token = generate_token(data, notify_admin.config["SECRET_KEY"], notify_admin.config["DANGEROUS_SALT"])

    page = client_request.get_url(url_for_endpoint_with_token(".new_password", token=token))
    assert "You can now create a new password for your account." in page.text

    mock_update_user_attribute.assert_called_once_with(user["id"], email_access_validated_at="2021-01-01T11:11:11")


def test_should_return_404_when_email_address_does_not_exist(
    notify_admin,
    client_request,
    mock_get_user_by_email_not_found,
):
    client_request.logout()
    data = json.dumps({"email": "no_user@d.gov.uk", "created_at": str(datetime.now(UTC))})
    token = generate_token(data, notify_admin.config["SECRET_KEY"], notify_admin.config["DANGEROUS_SALT"])
    client_request.get_url(
        url_for_endpoint_with_token(".new_password", token=token),
        _expected_status=404,
    )


@pytest.mark.parametrize(
    "redirect_url",
    [
        None,
        f"/services/{SERVICE_ONE_ID}/templates",
    ],
)
def test_should_redirect_to_two_factor_when_password_reset_is_successful(
    notify_admin,
    client_request,
    mock_get_user_by_email_request_password_reset,
    mock_send_verify_code,
    mock_reset_failed_login_count,
    redirect_url,
):
    client_request.logout()
    user = mock_get_user_by_email_request_password_reset.return_value
    data = json.dumps({"email": user["email_address"], "created_at": str(datetime.now(UTC))})
    token = generate_token(data, notify_admin.config["SECRET_KEY"], notify_admin.config["DANGEROUS_SALT"])
    client_request.post_url(
        url_for_endpoint_with_token(".new_password", token=token, next=redirect_url),
        _data={"new_password": "a-new_password"},
        _expected_redirect=url_for(".two_factor_sms", next=redirect_url),
    )
    mock_get_user_by_email_request_password_reset.assert_called_once_with(user["email_address"])


@pytest.mark.parametrize(
    "redirect_url",
    [
        None,
        f"/services/{SERVICE_ONE_ID}/templates",
    ],
)
def test_should_redirect_to_two_factor_webauthn_when_password_reset_is_successful(
    notify_admin,
    client_request,
    mock_get_user_by_email_request_password_reset,
    mock_send_verify_code,
    mock_reset_failed_login_count,
    redirect_url,
):
    client_request.logout()
    user = mock_get_user_by_email_request_password_reset.return_value
    user["auth_type"] = "webauthn_auth"
    data = json.dumps({"email": user["email_address"], "created_at": str(datetime.now(UTC))})
    token = generate_token(data, notify_admin.config["SECRET_KEY"], notify_admin.config["DANGEROUS_SALT"])
    client_request.post_url(
        url_for_endpoint_with_token(".new_password", token=token, next=redirect_url),
        _data={"new_password": "a-new_password"},
        _expected_redirect=url_for(".two_factor_webauthn", next=redirect_url),
    )
    mock_get_user_by_email_request_password_reset.assert_called_once_with(user["email_address"])

    assert not mock_send_verify_code.called
    assert mock_reset_failed_login_count.called


def test_should_redirect_index_if_user_has_already_changed_password(
    notify_admin,
    client_request,
    mock_get_user_by_email_user_changed_password,
    mock_send_verify_code,
    mock_reset_failed_login_count,
):
    client_request.logout()
    user = mock_get_user_by_email_user_changed_password.return_value
    data = json.dumps({"email": user["email_address"], "created_at": str(datetime.now(UTC))})
    token = generate_token(data, notify_admin.config["SECRET_KEY"], notify_admin.config["DANGEROUS_SALT"])
    client_request.post_url(
        url_for_endpoint_with_token(".new_password", token=token),
        _data={"new_password": "a-new_password"},
        _expected_redirect=url_for(".index"),
    )
    mock_get_user_by_email_user_changed_password.assert_called_once_with(user["email_address"])


def test_should_redirect_to_forgot_password_with_flash_message_when_token_is_expired(
    notify_admin, client_request, mocker
):
    client_request.logout()
    mocker.patch("app.main.views.new_password.check_token", side_effect=SignatureExpired("expired"))
    token = generate_token("foo@bar.com", notify_admin.config["SECRET_KEY"], notify_admin.config["DANGEROUS_SALT"])

    client_request.get_url(
        url_for_endpoint_with_token(".new_password", token=token),
        _expected_redirect=url_for(".forgot_password"),
    )


def test_should_sign_in_when_password_reset_is_successful_for_email_auth(
    notify_admin,
    client_request,
    api_user_active,
    mock_get_user_by_email_request_password_reset,
    mock_send_verify_code,
    mock_reset_failed_login_count,
    mock_update_user_password,
    mocker,
):
    client_request.logout()
    user = mock_get_user_by_email_request_password_reset.return_value
    mock_get_user = mocker.patch("app.user_api_client.get_user", return_value=api_user_active)
    user["auth_type"] = "email_auth"
    data = json.dumps({"email": user["email_address"], "created_at": str(datetime.now(UTC))})
    token = generate_token(data, notify_admin.config["SECRET_KEY"], notify_admin.config["DANGEROUS_SALT"])

    client_request.post_url(
        url_for_endpoint_with_token(".new_password", token=token),
        _data={"new_password": "a-new_password"},
        _expected_redirect=url_for(".show_accounts_or_dashboard"),
    )

    assert mock_get_user_by_email_request_password_reset.called
    assert mock_reset_failed_login_count.called

    # the log-in flow makes a couple of calls
    mock_get_user.assert_called_once_with(user["id"])
    mock_update_user_password.assert_called_once_with(user["id"], "a-new_password")

    assert not mock_send_verify_code.called

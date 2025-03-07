import json
import uuid
from unittest.mock import Mock

import pytest
from flask import session as flask_session
from flask import url_for
from itsdangerous import SignatureExpired
from notifications_python_client.errors import HTTPError

from app.main.views.verify import activate_user
from tests import organisation_json
from tests.conftest import create_user, normalize_spaces


def test_should_return_verify_template(
    client_request,
    api_user_active,
    mock_send_verify_code,
):
    client_request.logout()
    # TODO this lives here until we work out how to
    # reassign the session after it is lost mid register process
    with client_request.session_transaction() as session:
        session["user_details"] = {"email_address": api_user_active["email_address"], "id": api_user_active["id"]}
    page = client_request.get("main.verify")

    assert page.select_one("h1").text == "Check your phone"
    message = page.select("main p")[0].text
    assert message == "We’ve sent you a text message with a security code."


@pytest.mark.parametrize(
    "can_ask_to_join_a_service, expected_redirect, extra_args",
    (
        (False, "main.add_service", {}),
        (True, "main.your_services", {}),
    ),
)
def test_should_redirect_to_add_service_when_sms_code_is_correct(
    client_request,
    api_user_active,
    mocker,
    mock_check_verify_code,
    can_ask_to_join_a_service,
    expected_redirect,
    extra_args,
):
    api_user_active["current_session_id"] = str(uuid.UUID(int=1))
    mocker.patch("app.user_api_client.get_user", return_value=api_user_active)
    mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=organisation_json(can_ask_to_join_a_service=can_ask_to_join_a_service),
    )

    with client_request.session_transaction() as session:
        session["user_details"] = {"email_address": api_user_active["email_address"], "id": api_user_active["id"]}
        # user's only just created their account so no session in the cookie
        session.pop("current_session_id", None)

    client_request.post(
        "main.verify",
        _data={"sms_code": "12345"},
        _expected_redirect=url_for(expected_redirect, **extra_args),
    )

    # make sure the current_session_id has changed to what the API returned
    with client_request.session_transaction() as session:
        assert session["current_session_id"] == str(uuid.UUID(int=1))

    mock_check_verify_code.assert_called_once_with(api_user_active["id"], "12345", "sms")


def test_should_activate_user_after_verify(
    client_request,
    mocker,
    api_user_pending,
    mock_send_verify_code,
    mock_activate_user,
    mock_get_organisation_by_domain,
):
    client_request.logout()
    mocker.patch("app.user_api_client.get_user", return_value=api_user_pending)
    with client_request.session_transaction() as session:
        session["user_details"] = {"email_address": api_user_pending["email_address"], "id": api_user_pending["id"]}
    client_request.post("main.verify", _data={"sms_code": "12345"})
    assert mock_activate_user.called


def test_should_return_200_when_sms_code_is_wrong(
    client_request,
    api_user_active,
    mock_check_verify_code_code_not_found,
):
    with client_request.session_transaction() as session:
        session["user_details"] = {
            "email_address": api_user_active["email_address"],
            "id": api_user_active["id"],
        }

    page = client_request.post(
        "main.verify",
        _data={"sms_code": "12345"},
        _expected_status=200,
    )

    assert len(page.select(".govuk-error-message")) == 1
    assert "Code not found" in page.select_one(".govuk-error-message").text


def test_verify_email_redirects_to_verify_if_token_valid(
    client_request,
    mocker,
    api_user_pending,
    mock_get_user_pending,
    mock_send_verify_code,
    mock_check_verify_code,
):
    token_data = {"user_id": api_user_pending["id"], "secret_code": "UNUSED"}
    mocker.patch("app.main.views.verify.check_token", return_value=json.dumps(token_data))

    client_request.get(
        "main.verify_email",
        token="notreal",
        _expected_redirect=url_for("main.verify"),
    )

    assert not mock_check_verify_code.called
    mock_send_verify_code.assert_called_once_with(api_user_pending["id"], "sms", api_user_pending["mobile_number"])

    with client_request.session_transaction() as session:
        assert session["user_details"] == {"email": api_user_pending["email_address"], "id": api_user_pending["id"]}


def test_verify_email_doesnt_verify_sms_if_user_on_email_auth(
    client_request,
    mocker,
    mock_send_verify_code,
    mock_check_verify_code,
    mock_activate_user,
    fake_uuid,
    mock_get_organisation_by_domain,
):
    pending_user_with_email_auth = create_user(auth_type="email_auth", state="pending", id=fake_uuid)

    mocker.patch("app.user_api_client.get_user", return_value=pending_user_with_email_auth)
    token_data = {"user_id": pending_user_with_email_auth["id"], "secret_code": "UNUSED"}
    mocker.patch("app.main.views.verify.check_token", return_value=json.dumps(token_data))

    client_request.get(
        "main.verify_email",
        token="notreal",
        _expected_redirect=url_for("main.add_service"),
    )

    assert not mock_check_verify_code.called
    assert not mock_send_verify_code.called

    mock_activate_user.assert_called_once_with(pending_user_with_email_auth["id"])

    # user is logged in
    with client_request.session_transaction() as session:
        assert session["user_id"] == pending_user_with_email_auth["id"]


def test_verify_email_redirects_to_email_sent_if_token_expired(
    client_request,
    mocker,
):
    client_request.logout()
    mocker.patch("app.main.views.verify.check_token", side_effect=SignatureExpired("expired"))

    client_request.get(
        "main.verify_email",
        token="notreal",
        _expected_redirect=url_for("main.resend_email_verification"),
    )


def test_verify_email_shows_flash_message_if_token_expired(
    client_request,
    mocker,
):
    client_request.logout()
    mocker.patch("app.main.views.verify.check_token", side_effect=SignatureExpired("expired"))

    page = client_request.get(
        "main.verify_email",
        token="notreal",
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        "The link in the email we sent you has expired. We’ve sent you a new one."
    )


def test_verify_email_redirects_to_sign_in_if_user_active(
    client_request,
    mocker,
    api_user_active,
    mock_send_verify_code,
):
    client_request.logout()
    token_data = {"user_id": api_user_active["id"], "secret_code": 12345}
    mocker.patch("app.main.views.verify.check_token", return_value=json.dumps(token_data))

    page = client_request.get("main.verify_email", token="notreal", _follow_redirects=True)

    assert page.select_one("h1").text == "Sign in"
    flash_banner = page.select_one("div.banner-dangerous").string.strip()
    assert flash_banner == "That verification link has expired."


def test_verify_redirects_to_sign_in_if_not_logged_in(client_request):
    client_request.logout()
    client_request.get(
        "main.verify",
        _expected_redirect=url_for("main.sign_in"),
    )


def test_activate_user_redirects_to_service_dashboard_if_user_already_belongs_to_service(
    client_request,
    service_one,
    sample_invite,
    api_user_active,
    mock_get_invited_user_by_id,
    mocker,
):
    mocker.patch(
        "app.user_api_client.add_user_to_service",
        side_effect=HTTPError(
            response=Mock(
                status_code=400,
                json={
                    "result": "error",
                    "message": {f"User id: {api_user_active['id']} already part of service id: {service_one['id']}"},
                },
            ),
            message=f"User id: {api_user_active['id']} already part of service id: {service_one['id']}",
        ),
    )

    # Can't use `with client.session_transaction()...` here since activate_session is not a view function
    flask_session["invited_user_id"] = sample_invite["id"]

    response = activate_user(api_user_active["id"])

    assert response.location == url_for("main.service_dashboard", service_id=service_one["id"])

    flask_session.pop("invited_user_id")

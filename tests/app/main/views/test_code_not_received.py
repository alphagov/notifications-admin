import pytest
from flask import url_for
from freezegun import freeze_time

from tests.conftest import SERVICE_ONE_ID


def test_should_render_email_verification_resend_show_email_address_and_resend_verify_email(
    client_request,
    mocker,
    api_user_active,
    mock_get_user_by_email,
    mock_send_verify_email,
):
    client_request.logout()
    with client_request.session_transaction() as session:
        session["user_details"] = {"id": api_user_active["id"], "email": api_user_active["email_address"]}
    page = client_request.get("main.resend_email_verification")

    assert page.select_one("h1").string == "Check your email"
    expected = f"A new confirmation email has been sent to {api_user_active['email_address']}"

    message = page.select("main p")[0].text
    assert message == expected
    mock_send_verify_email.assert_called_with(api_user_active["id"], api_user_active["email_address"])


@pytest.mark.parametrize(
    "redirect_url",
    [
        None,
        f"/services/{SERVICE_ONE_ID}/templates",
    ],
)
def test_should_render_correct_resend_template_for_active_user(
    client_request, api_user_active, mock_get_user_by_email, mock_send_verify_code, redirect_url
):
    client_request.logout()
    with client_request.session_transaction() as session:
        session["user_details"] = {"id": api_user_active["id"], "email": api_user_active["email_address"]}
    page = client_request.get("main.check_and_resend_text_code", next=redirect_url)

    assert page.select_one("h1").string == "If you do not receive a security code"
    # there shouldn't be a form for updating mobile number
    assert page.select_one("form") is None
    assert page.select_one("a.govuk-button")["href"] == url_for(
        "main.check_and_resend_verification_code", next=redirect_url
    )


def test_should_render_correct_resend_template_for_pending_user(
    client_request,
    mocker,
    api_user_pending,
    mock_send_verify_code,
):
    client_request.logout()
    mocker.patch("app.user_api_client.get_user_by_email", return_value=api_user_pending)

    with client_request.session_transaction() as session:
        session["user_details"] = {"id": api_user_pending["id"], "email": api_user_pending["email_address"]}
    page = client_request.get("main.check_and_resend_text_code")

    assert page.select_one("h1").string == "If you do not receive a security code"

    expected = "Check that you can receive text messages from other numbers."
    message = page.select("main li")[0].text
    assert message == expected
    assert page.select_one("form").input["value"] == api_user_pending["mobile_number"]


@pytest.mark.parametrize(
    "redirect_url",
    [
        None,
        f"/services/{SERVICE_ONE_ID}/templates",
    ],
)
@pytest.mark.parametrize(
    "phone_number_to_register_with",
    [
        "+447700900460",
        "+1800-555-555",
    ],
)
def test_should_resend_verify_code_and_update_mobile_for_pending_user(
    client_request,
    mocker,
    api_user_pending,
    mock_update_user_attribute,
    mock_send_verify_code,
    phone_number_to_register_with,
    redirect_url,
):
    client_request.logout()
    mock_update_user_attribute.reset_mock()
    mocker.patch("app.user_api_client.get_user_by_email", return_value=api_user_pending)

    with client_request.session_transaction() as session:
        session["user_details"] = {"id": api_user_pending["id"], "email": api_user_pending["email_address"]}

    client_request.post(
        "main.check_and_resend_text_code",
        next=redirect_url,
        _data={"mobile_number": phone_number_to_register_with},
        _expected_redirect=url_for("main.verify", next=redirect_url),
    )

    mock_update_user_attribute.assert_called_once_with(
        api_user_pending["id"],
        mobile_number=phone_number_to_register_with,
    )
    mock_send_verify_code.assert_called_once_with(
        api_user_pending["id"],
        "sms",
        phone_number_to_register_with,
    )


@pytest.mark.parametrize(
    "redirect_url",
    [
        None,
        f"/services/{SERVICE_ONE_ID}/templates",
    ],
)
def test_check_and_redirect_to_two_factor_if_user_active(
    client_request, api_user_active, mock_get_user_by_email, mock_send_verify_code, redirect_url
):
    client_request.logout()
    with client_request.session_transaction() as session:
        session["user_details"] = {"id": api_user_active["id"], "email": api_user_active["email_address"]}
    client_request.get(
        "main.check_and_resend_verification_code",
        next=redirect_url,
        _expected_redirect=url_for("main.two_factor_sms", next=redirect_url),
    )


@pytest.mark.parametrize(
    "redirect_url",
    [
        None,
        f"/services/{SERVICE_ONE_ID}/templates",
    ],
)
def test_check_and_redirect_to_verify_if_user_pending(
    client_request, mocker, api_user_pending, mock_get_user_pending, mock_send_verify_code, redirect_url
):
    client_request.logout()
    mocker.patch("app.user_api_client.get_user_by_email", return_value=api_user_pending)

    with client_request.session_transaction() as session:
        session["user_details"] = {"id": api_user_pending["id"], "email": api_user_pending["email_address"]}

    client_request.get(
        "main.check_and_resend_verification_code",
        next=redirect_url,
        _expected_redirect=url_for("main.verify", next=redirect_url),
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "main.resend_email_verification",
        "main.check_and_resend_text_code",
        "main.check_and_resend_verification_code",
    ],
)
def test_redirect_to_sign_in_if_not_logged_in(
    client_request,
    endpoint,
):
    client_request.logout()
    client_request.get(
        endpoint,
        _expected_redirect=url_for("main.sign_in"),
    )


@freeze_time("2020-11-27T12:00:00")
@pytest.mark.parametrize(
    ("redirect_url", "email_access_validated_at"),
    [
        (None, "2020-11-23T11:35:21.726132Z"),  # login_via_sms = False
        (f"/services/{SERVICE_ONE_ID}/templates", "2020-11-23T11:35:21.726132Z"),
    ],
)
def test_should_render_correct_email_not_received_template_for_active_user(
    client_request,
    api_user_active,
    mock_get_user_by_email,
    mock_send_verify_code,
    redirect_url,
    email_access_validated_at,
):
    client_request.logout()
    with client_request.session_transaction() as session:
        session["user_details"] = {"id": api_user_active["id"], "email": api_user_active["email_address"]}
    api_user_active["email_access_validated_at"] = email_access_validated_at

    page = client_request.get("main.email_not_received", next=redirect_url)

    assert page.select_one("h1").string == "If you do not receive an email link"
    # there shouldn't be a form for updating mobile number
    assert page.select_one("form") is None
    assert page.select_one("a.govuk-button")["href"] == url_for("main.resend_email_link", next=redirect_url)

from unittest.mock import ANY

import pytest
from flask import url_for

from app.models.user import User
from tests.conftest import normalize_spaces


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_render_register_returns_template_with_form(
    client_request,
):
    client_request.logout()
    page = client_request.get_url("/register")

    assert page.select_one("input[name=auth_type]")["value"] == "sms_auth"
    assert page.select_one("#email_address")["spellcheck"] == "false"
    assert page.select_one("#email_address")["autocomplete"] == "email"
    assert page.select_one("#password")["autocomplete"] == "new-password"

    assert normalize_spaces(page.select("main p")[0].text) == (
        "When you create an account you accept our terms of use."
    )
    assert "Create an account" in page.text


def test_logged_in_user_redirects_to_account(
    client_request,
):
    client_request.get(
        "main.register",
        _expected_status=302,
        _expected_redirect=url_for("main.show_accounts_or_dashboard"),
    )


@pytest.mark.parametrize(
    "phone_number_to_register_with",
    [
        "+4407700900460",
        "+1 202-555-0104",
    ],
)
@pytest.mark.parametrize(
    "password",
    [
        "the quick brown fox",
        "   the   quick   brown   fox   ",
    ],
)
@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
@pytest.mark.parametrize(
    "name",
    (
        "Some One Valid",
        "Mr. Firstname Lastname",  # dots are fine
        "test@example.com",  # email addresses are fine (lots of users do this for some reason)
    ),
)
def test_register_creates_new_user_and_redirects_to_continue_page(
    client_request,
    mock_send_verify_code,
    mock_register_user,
    mock_get_user_by_email_not_found,
    mock_email_is_not_already_in_use,
    mock_send_verify_email,
    phone_number_to_register_with,
    password,
    name,
):
    client_request.logout()
    user_data = {
        "name": name,
        "email_address": "notfound@example.gov.uk",
        "mobile_number": phone_number_to_register_with,
        "password": password,
        "auth_type": "sms_auth",
    }

    page = client_request.post(
        "main.register",
        _data=user_data,
        _follow_redirects=True,
    )

    assert page.select("main p")[0].text == "An email has been sent to notfound@example.gov.uk."

    mock_send_verify_email.assert_called_with(ANY, user_data["email_address"])
    mock_register_user.assert_called_with(
        user_data["name"],
        user_data["email_address"],
        user_data["mobile_number"],
        user_data["password"],
        user_data["auth_type"],
    )


def test_register_continue_handles_missing_session_sensibly(
    client_request,
):
    client_request.logout()
    # session is not set
    client_request.get(
        "main.registration_continue",
        _expected_redirect=url_for("main.show_accounts_or_dashboard"),
    )


@pytest.mark.skip(reason="[NOTIFYNL] Missing mock in overriden views")
@pytest.mark.parametrize(
    "name",
    (
        "https://example.com",
        "firstname http://example.com lastname",
        "click [here](http://example.com)",
        "click [here](example.com)",
        "example.com/index.html?foo=bar#baz",
    ),
)
def test_register_form_returns_error_when_name_contains_url(
    client_request,
    name,
):
    client_request.logout()
    page = client_request.post(
        "main.register",
        _data={
            "name": name,
            "email_address": "bad_mobile@example.gov.uk",
            "mobile_number": "not good",
            "password": "validPassword!",
        },
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one(".govuk-error-message").text) == (
        "Error: Your full name cannot contain a URL"
    )


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_process_register_returns_200_when_mobile_number_is_invalid(
    client_request,
):
    client_request.logout()
    page = client_request.post(
        "main.register",
        _data={
            "name": "Bad Mobile",
            "email_address": "bad_mobile@example.gov.uk",
            "mobile_number": "not good",
            "password": "validPassword!",
        },
        _expected_status=200,
    )

    assert "Mobile numbers can only include: 0 1 2 3 4 5 6 7 8 9 ( ) + -" in page.text


def test_should_return_200_when_email_is_not_gov_uk(
    client_request,
    mock_get_organisations,
):
    client_request.logout()
    page = client_request.post(
        "main.register",
        _data={
            "name": "Firstname Lastname",
            "email_address": "bad_mobile@example.not.right",
            "mobile_number": "07900900123",
            "password": "validPassword!",
        },
        _expected_status=200,
    )

    assert "Enter a public sector email address or find out who can use Notify" in normalize_spaces(
        page.select_one(".govuk-error-message").text
    )
    assert page.select_one(".govuk-error-message a")["href"] == url_for("main.guidance_who_can_use_notify")


@pytest.mark.parametrize(
    "email_address",
    (
        "notfound@example.gov.uk",
        "example@lsquo.net",
        pytest.param("example@ellipsis.com", marks=pytest.mark.xfail(raises=AssertionError)),
    ),
)
@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_should_add_user_details_to_session(
    client_request,
    mock_send_verify_code,
    mock_register_user,
    mock_get_user_by_email_not_found,
    mock_get_organisations_with_unusual_domains,
    mock_email_is_not_already_in_use,
    mock_send_verify_email,
    email_address,
):
    client_request.logout()
    client_request.post(
        "main.register",
        _data={
            "name": "Test Codes",
            "email_address": email_address,
            "mobile_number": "+4407700900460",
            "password": "validPassword!",
        },
    )
    with client_request.session_transaction() as session:
        assert session["user_details"]["email"] == email_address


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_should_return_200_if_password_is_on_list_of_commonly_used_passwords(
    client_request,
    mock_get_user_by_email,
):
    client_request.logout()
    page = client_request.post(
        "main.register",
        _data={
            "name": "Bad Mobile",
            "email_address": "bad_mobile@example.gov.uk",
            "mobile_number": "+44123412345",
            "password": "password",
        },
        _expected_status=200,
    )

    assert "Choose a password that’s harder to guess" in page.text


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_register_with_existing_email_sends_emails(
    client_request,
    api_user_active,
    mock_get_user_by_email,
    mock_send_already_registered_email,
):
    client_request.logout()
    user_data = {
        "name": "Already Hasaccount",
        "email_address": api_user_active["email_address"],
        "mobile_number": "+4407700900460",
        "password": "validPassword!",
    }

    client_request.post(
        "main.register",
        _data=user_data,
        _expected_redirect=url_for("main.registration_continue"),
    )


@pytest.mark.parametrize(
    "email_address, expected_value, extra_args",
    [
        ("first.last@example.com", "First Last", {}),
        ("first.middle.last@example.com", "First Middle Last", {}),
        ("first.m.last@example.com", "First Last", {}),
        ("first.last-last@example.com", "First Last-Last", {}),
        ("first.o'last@example.com", "First O’Last", {"_test_for_non_smart_quotes": False}),
        ("first.last+testing@example.com", "First Last", {}),
        ("first.last+testing+testing@example.com", "First Last", {}),
        ("first.last6@example.com", "First Last", {}),
        ("first.last.212@example.com", "First Last", {}),
        ("first.2.last@example.com", "First Last", {}),
        ("first.2b.last@example.com", "First Last", {}),
        ("first.1.2.3.last@example.com", "First Last", {}),
        ("first.last.1.2.3@example.com", "First Last", {}),
        # Instances where we can’t make a good-enough guess:
        ("example123@example.com", None, {}),
        ("f.last@example.com", None, {}),
        ("f.m.last@example.com", None, {}),
    ],
)
def test_shows_name_on_registration_page_from_invite(
    client_request,
    email_address,
    expected_value,
    extra_args,
    sample_invite,
    mock_get_invited_user_by_id,
):
    sample_invite["email_address"] = email_address
    with client_request.session_transaction() as session:
        session["invited_user_id"] = sample_invite

    page = client_request.get(
        "main.register_from_invite",
        **extra_args,
    )
    assert page.select_one("input[name=name]").get("value") == expected_value


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_shows_hidden_email_address_on_registration_page_from_invite(
    client_request,
    sample_invite,
    mock_get_invited_user_by_id,
):
    with client_request.session_transaction() as session:
        session["invited_user_id"] = sample_invite

    page = client_request.get("main.register_from_invite")
    assert normalize_spaces(page.select_one("main p").text) == (
        "Your account will be created with this email address: invited_user@test.gov.uk"
    )
    hidden_input = page.select_one("form .govuk-visually-hidden input")
    for attr, value in (
        ("type", "email"),
        ("name", "username"),
        ("id", "username"),
        ("value", "invited_user@test.gov.uk"),
        ("disabled", "disabled"),
        ("tabindex", "-1"),
        ("aria-hidden", "true"),
        ("autocomplete", "username"),
    ):
        assert hidden_input[attr] == value


@pytest.mark.parametrize(
    "extra_data",
    (
        {},
        # The username field is present in the page but the POST request
        # should ignore it
        {"username": "invited@user.com"},
        {"username": "anythingelse@example.com"},
    ),
)
def test_register_from_invite(
    client_request,
    mock_email_is_not_already_in_use,
    mock_register_user,
    mock_send_verify_code,
    mock_accept_invite,
    mock_get_invited_user_by_id,
    sample_invite,
    extra_data,
):
    client_request.logout()
    with client_request.session_transaction() as session:
        session["invited_user_id"] = sample_invite["id"]
    client_request.post(
        "main.register_from_invite",
        _data=dict(
            name="Registered in another Browser",
            email_address=sample_invite["email_address"],
            mobile_number="+4407700900460",
            service=sample_invite["service"],
            password="somreallyhardthingtoguess",
            auth_type="sms_auth",
            **extra_data,
        ),
        _expected_redirect=url_for("main.verify"),
    )
    mock_register_user.assert_called_once_with(
        "Registered in another Browser",
        sample_invite["email_address"],
        "+4407700900460",
        "somreallyhardthingtoguess",
        "sms_auth",
    )
    mock_get_invited_user_by_id.assert_called_once_with(sample_invite["id"])


def test_register_from_invite_when_user_registers_in_another_browser(
    client_request,
    api_user_active,
    mock_get_user_by_email,
    mock_accept_invite,
    mock_get_invited_user_by_id,
    sample_invite,
):
    client_request.logout()
    sample_invite["email_address"] = api_user_active["email_address"]
    with client_request.session_transaction() as session:
        session["invited_user_id"] = sample_invite["id"]
    client_request.post(
        "main.register_from_invite",
        _data={
            "name": "Registered in another Browser",
            "email_address": api_user_active["email_address"],
            "mobile_number": api_user_active["mobile_number"],
            "service": sample_invite["service"],
            "password": "somreallyhardthingtoguess",
            "auth_type": "sms_auth",
        },
        _expected_redirect=url_for("main.verify"),
    )


@pytest.mark.parametrize("invite_email_address", ["gov-user@gov.uk", "non-gov-user@example.com"])
def test_register_from_email_auth_invite(
    client_request,
    sample_invite,
    mock_email_is_not_already_in_use,
    mock_register_user,
    mock_send_verify_email,
    mock_send_verify_code,
    mock_accept_invite,
    mock_create_event,
    mock_add_user_to_service,
    mock_get_service,
    mock_get_invited_user_by_id,
    invite_email_address,
    service_one,
    fake_uuid,
    mocker,
):
    client_request.logout()
    mock_login_user = mocker.patch("app.models.user.login_user")
    sample_invite["auth_type"] = "email_auth"
    sample_invite["email_address"] = invite_email_address
    with client_request.session_transaction() as session:
        session["invited_user_id"] = sample_invite["id"]
        # Prove that the user isn’t already signed in
        assert "user_id" not in session

    data = {
        "name": "invited user",
        "email_address": sample_invite["email_address"],
        "mobile_number": "07700900001",
        "password": "FSLKAJHFNvdzxgfyst",
        "service": sample_invite["service"],
        "auth_type": "email_auth",
    }

    client_request.post(
        "main.register_from_invite",
        _data=data,
        _expected_redirect=url_for(
            "main.service_dashboard",
            service_id=sample_invite["service"],
        ),
    )

    # doesn't send any 2fa code
    assert not mock_send_verify_email.called
    assert not mock_send_verify_code.called
    # creates user with email_auth set
    mock_register_user.assert_called_once_with(
        data["name"], data["email_address"], data["mobile_number"], data["password"], data["auth_type"]
    )
    # this is actually called twice, at the beginning of the function and then by the activate_user function
    mock_get_invited_user_by_id.assert_called_with(sample_invite["id"])
    mock_accept_invite.assert_called_once_with(sample_invite["service"], sample_invite["id"])

    # just logs them in
    mock_login_user.assert_called_once_with(
        User({"id": fake_uuid, "platform_admin": False})  # This ID matches the return value of mock_register_user
    )
    mock_add_user_to_service.assert_called_once_with(
        sample_invite["service"],
        fake_uuid,  # This ID matches the return value of mock_register_user
        {"manage_api_keys", "manage_service", "send_messages", "view_activity"},
        [],
    )

    with client_request.session_transaction() as session:
        # The user is signed in
        assert "user_id" in session
        # invited user details are still there so they can get added to the service
        assert session["invited_user_id"] == sample_invite["id"]


def test_can_register_email_auth_without_phone_number(
    client_request,
    sample_invite,
    mock_email_is_not_already_in_use,
    mock_register_user,
    mock_get_user,
    mock_send_verify_email,
    mock_accept_invite,
    mock_create_event,
    mock_add_user_to_service,
    mock_get_invited_user_by_id,
):
    client_request.logout()
    sample_invite["auth_type"] = "email_auth"
    with client_request.session_transaction() as session:
        session["invited_user_id"] = sample_invite["id"]

    data = {
        "name": "invited user",
        "email_address": sample_invite["email_address"],
        "mobile_number": "",
        "password": "FSLKAJHFNvdzxgfyst",
        "service": sample_invite["service"],
        "auth_type": "email_auth",
    }

    client_request.post(
        "main.register_from_invite",
        _data=data,
        _expected_redirect=url_for(
            "main.service_dashboard",
            service_id=sample_invite["service"],
        ),
    )

    mock_register_user.assert_called_once_with(ANY, ANY, None, ANY, ANY)  # mobile_number


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
def test_cannot_register_with_sms_auth_and_missing_mobile_number(
    client_request,
    mock_send_verify_code,
    mock_get_user_by_email_not_found,
):
    client_request.logout()
    page = client_request.post(
        "main.register",
        _data={
            "name": "Missing Mobile",
            "email_address": "missing_mobile@example.gov.uk",
            "password": "validPassword!",
        },
        _expected_status=200,
    )

    err = page.select_one(".govuk-error-message")
    assert err.text.strip() == "Error: Enter a mobile number"


def test_register_from_invite_form_doesnt_show_mobile_number_field_if_email_auth(
    client_request,
    sample_invite,
    mock_get_invited_user_by_id,
):
    client_request.logout()
    sample_invite["auth_type"] = "email_auth"
    with client_request.session_transaction() as session:
        session["invited_user_id"] = sample_invite["id"]

    page = client_request.get("main.register_from_invite")

    assert page.select_one("input[name=auth_type]")["value"] == "email_auth"
    assert page.select_one("input[name=mobile_number]") is None

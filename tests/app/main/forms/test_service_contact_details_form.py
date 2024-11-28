import pytest

from app.main.forms import ServiceContactDetailsForm


def test_form_fails_validation_with_no_radio_buttons_selected(notify_admin):
    with notify_admin.test_request_context(method="POST", data={}):
        form = ServiceContactDetailsForm()

        assert not form.validate_on_submit()
        assert len(form.errors) == 1
        assert form.errors["contact_details_type"] == ["Select an option"]


@pytest.mark.parametrize(
    "selected_radio_button, selected_text_box, text_box_data, error_message",
    [
        ("email_address", "url", "http://www.example.com", "Enter an email address"),
        ("phone_number", "url", "http://www.example.com", "Enter a phone number"),
        ("url", "email_address", "user@example.com", "Enter a URL in the correct format"),
        ("phone_number", "email_address", "user@example.com", "Enter a phone number"),
        ("url", "phone_number", "0207 123 4567", "Enter a URL in the correct format"),
        ("email_address", "phone_number", "0207 123 4567", "Enter an email address"),
    ],
)
def test_form_fails_validation_when_radio_button_selected_and_text_box_filled_in_do_not_match(
    notify_admin, selected_radio_button, selected_text_box, text_box_data, error_message
):
    data = {"contact_details_type": selected_radio_button, selected_text_box: text_box_data}

    with notify_admin.test_request_context(method="POST", data=data):
        form = ServiceContactDetailsForm()

        assert not form.validate_on_submit()
        assert len(form.errors) == 1
        assert form.errors[selected_radio_button] == [error_message]


@pytest.mark.parametrize(
    "selected_field, url, email_address, phone_number",
    [
        ("url", "http://www.example.com", "invalid-email.com", "phone"),
        ("email_address", "www.invalid-url.com", "me@example.com", "phone"),
        ("phone_number", "www.invalid-url.com", "invalid-email.com", "0207 123 4567"),
    ],
)
def test_form_only_validates_the_field_which_matches_the_selected_radio_button(
    notify_admin,
    selected_field,
    url,
    email_address,
    phone_number,
):
    data = {
        "contact_details_type": selected_field,
        "url": url,
        "email_address": email_address,
        "phone_number": phone_number,
    }

    with notify_admin.test_request_context(method="POST", data=data):
        form = ServiceContactDetailsForm()

        assert form.validate_on_submit()


def test_form_url_validation_fails_with_invalid_url_field(notify_admin):
    data = {"contact_details_type": "url", "url": "www.example.com"}

    with notify_admin.test_request_context(method="POST", data=data):
        form = ServiceContactDetailsForm()

        assert not form.validate_on_submit()
        assert len(form.errors) == 1
        assert len(form.errors["url"]) == 1


def test_form_email_validation_fails_with_invalid_email_address_field(notify_admin):
    data = {"contact_details_type": "email_address", "email_address": "1@co"}

    with notify_admin.test_request_context(method="POST", data=data):
        form = ServiceContactDetailsForm()

        assert not form.validate_on_submit()
        assert len(form.errors) == 1
        assert len(form.errors["email_address"]) == 2


def test_form_phone_number_validation_fails_with_invalid_phone_number_field(notify_admin):
    data = {"contact_details_type": "phone_number", "phone_number": "1235 A"}

    with notify_admin.test_request_context(method="POST", data=data):
        form = ServiceContactDetailsForm()

        assert not form.validate_on_submit()
        assert len(form.errors) == 1
        assert "Enter a phone number in the correct format" in form.errors["phone_number"]


@pytest.mark.parametrize(
    "short_number, allowed",
    (
        ("119", True),
        ("999", False),
        ("112", False),
        (" 999 ", False),
        ("(9)99", False),
        ("9-9-9", False),
    ),
)
def test_form_phone_number_allows_non_emergency_3_digit_numbers(notify_admin, short_number, allowed):
    data = {"contact_details_type": "phone_number", "phone_number": short_number}

    with notify_admin.test_request_context(method="POST", data=data):
        form = ServiceContactDetailsForm()
        if allowed:
            assert form.validate_on_submit()
            assert len(form.errors) == 0
            assert form.errors == {}
        else:
            assert not form.validate_on_submit()
            assert len(form.errors) == 1
            assert form.errors["phone_number"] == ["Phone number cannot be an emergency number"]


@pytest.mark.parametrize(
    "short_number, allowed",
    (("01572 812241 7081", True),),
)
def test_form_phone_number_allows_non_emergency_numbers_with_extensions(notify_admin, short_number, allowed):
    data = {"contact_details_type": "phone_number", "phone_number": short_number}

    with notify_admin.test_request_context(method="POST", data=data):
        form = ServiceContactDetailsForm()
        assert form.validate_on_submit()
        assert len(form.errors) == 0
        assert form.errors == {}

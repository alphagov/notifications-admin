from unittest.mock import Mock

import pytest
from notifications_utils.recipient_validation.errors import InvalidPhoneError
from wtforms import ValidationError

from app.main.validators import (
    CharactersNotAllowed,
    MustContainAlphanumericCharacters,
    NoCommasInPlaceHolders,
    OnlySMSCharacters,
    StringsNotAllowed,
    ValidGovEmail,
    ValidPhoneNumber,
)


def _gen_mock_field(x, **kwargs):
    return Mock(data=x, **kwargs)


@pytest.mark.parametrize(
    "email",
    [
        "test@gov.uk",
        "test@GOV.UK",
        "test@gov.uK",
        "test@test.test.gov.uk",
        "test@test.gov.uk",
        "test@nhs.uk",
        "test@gov.nhs.uk",
        "test@nhs.net",
        "test@gov.nhs.net",
        "test@nhs.scot",
        "test@police.uk",
        "test@gov.police.uk",
        "test@GOV.PoliCe.uk",
        "test@cjsm.net",
        "test@example.ac.uk",
        "test@example.sch.uk",
    ],
)
def test_valid_list_of_white_list_email_domains(
    client_request,
    email,
):
    email_domain_validators = ValidGovEmail()
    email_domain_validators(None, _gen_mock_field(email))


@pytest.mark.parametrize(
    "email",
    [
        "test@ukgov.uk",
        "test@gov.uk.uk",
        "test@gov.test.uk",
        "test@ukmod.uk",
        "test@mod.uk.uk",
        "test@mod.test.uk",
        "test@ukddc-mod.org",
        "test@ddc-mod.org.uk",
        "test@ddc-mod.uk.org",
        "test@ukgov.scot",
        "test@gov.scot.uk",
        "test@gov.test.scot",
        "test@ukparliament.uk",
        "test@parliament.uk.uk",
        "test@parliament.test.uk",
        "test@uknhs.uk",
        "test@nhs.uk.uk",
        "test@uknhs.net",
        "test@nhs.net.uk",
        "test@nhs.test.net",
        "test@ukpolice.uk",
        "test@police.uk.uk",
        "test@police.test.uk",
        "test@ucds.com",
        "test@123bl.uk",
    ],
)
def test_invalid_list_of_white_list_email_domains(
    client_request,
    email,
    mock_get_organisations,
):
    email_domain_validators = ValidGovEmail()
    with pytest.raises(ValidationError):
        email_domain_validators(None, _gen_mock_field(email))


def test_uk_mobile_number_validation_messages_match(mocker):
    mock_field = _gen_mock_field("notanumber", error_summary_messages=[])
    mocker.patch(
        "app.main.validators.PhoneNumber",
        side_effect=InvalidPhoneError(code=InvalidPhoneError.Codes.UNKNOWN_CHARACTER),
    )
    with pytest.raises(ValidationError) as error:
        ValidPhoneNumber()(None, mock_field)

    assert str(error.value) == InvalidPhoneError.ERROR_MESSAGES[InvalidPhoneError.Codes.UNKNOWN_CHARACTER]
    assert mock_field.error_summary_messages == ["%s can only include: 0 1 2 3 4 5 6 7 8 9 ( ) + -"]


def test_for_commas_in_placeholders(
    client_request,
):
    with pytest.raises(ValidationError) as error:
        NoCommasInPlaceHolders()(None, _gen_mock_field("Hello ((name,date))"))
    assert str(error.value) == "You cannot put commas between double brackets"
    NoCommasInPlaceHolders()(None, _gen_mock_field("Hello ((name))"))


@pytest.mark.parametrize("msg", ["The quick brown fox", "Thé “quick” bröwn fox\u200b"])
def test_sms_character_validation(client_request, msg):
    OnlySMSCharacters(template_type="sms")(None, _gen_mock_field(msg))


@pytest.mark.parametrize(
    "data, err_msg",
    [
        (
            "∆ abc 📲 def 📵 ghi",
            "You cannot use ∆, 📲 or 📵 in text messages. These characters will not display properly on some phones.",
        ),
        ("📵", "You cannot use 📵 in text messages. It will not display properly on some phones."),
    ],
)
def test_non_sms_character_validation(data, err_msg, client_request):
    with pytest.raises(ValidationError) as error:
        OnlySMSCharacters(template_type="sms")(None, _gen_mock_field(data))

    assert str(error.value) == err_msg


@pytest.mark.parametrize("string", [".", "A.", ".8...."])
def test_if_string_does_not_contain_alphanumeric_characters_raises(string):
    with pytest.raises(ValidationError) as error:
        MustContainAlphanumericCharacters()(None, _gen_mock_field(string))

    assert str(error.value) == "Must include at least two alphanumeric characters"


@pytest.mark.parametrize("string", [".A8", "AB.", ".42...."])
def test_if_string_contains_alphanumeric_characters_does_not_raise(string):
    MustContainAlphanumericCharacters()(None, _gen_mock_field(string))


def test_string_cannot_contain_characters():
    mock_field = _gen_mock_field("abc", error_summary_messages=[])
    with pytest.raises(ValidationError) as error:
        CharactersNotAllowed("abcdef")(None, mock_field)

    assert str(error.value) == "Cannot contain a, b or c"
    assert mock_field.error_summary_messages == ["%s cannot contain a, b or c"]


def test_string_cannot_contain_characters_with_custom_error_message():
    mock_field = _gen_mock_field("abc", error_summary_messages=[])
    with pytest.raises(ValidationError) as error:
        CharactersNotAllowed(
            "abcdef",
            message="Cannot use first 3 letters of the alphabet",
            error_summary_message="%s cannot use first 3 letters of the alphabet",
        )(None, mock_field)

    assert str(error.value) == "Cannot use first 3 letters of the alphabet"
    assert mock_field.error_summary_messages == ["%s cannot use first 3 letters of the alphabet"]


@pytest.mark.parametrize(
    "field_value, expected_error, expected_error_summary_messages",
    (
        ("abc", "Cannot be ‘abc’", ["%s cannot be ‘abc’"]),
        ("ABC", "Cannot be ‘abc’", ["%s cannot be ‘abc’"]),
        ("123", "Cannot be ‘123’", ["%s cannot be ‘123’"]),
        pytest.param(
            "abc123",
            "Cannot be ‘abc’",
            ["%s cannot be ‘abc’"],
            marks=pytest.mark.xfail(reason="Shouldn’t match on substrings"),
        ),
    ),
)
def test_string_cannot_contain_string(field_value, expected_error, expected_error_summary_messages):
    mock_field = _gen_mock_field(field_value, error_summary_messages=[])
    with pytest.raises(ValidationError) as error:
        StringsNotAllowed("abc", "123")(None, mock_field)

    assert str(error.value) == expected_error
    assert mock_field.error_summary_messages == expected_error_summary_messages


@pytest.mark.parametrize(
    "field_value, expected_error, expected_error_summary_messages",
    (
        ("abc", "Cannot contain ‘abc’", ["%s cannot contain ‘abc’"]),
        ("ABC", "Cannot contain ‘abc’", ["%s cannot contain ‘abc’"]),
        ("123", "Cannot contain ‘123’", ["%s cannot contain ‘123’"]),
        ("abc123", "Cannot contain ‘abc’", ["%s cannot contain ‘abc’"]),
    ),
)
def test_string_cannot_contain_substrings(field_value, expected_error, expected_error_summary_messages):
    mock_field = _gen_mock_field(field_value, error_summary_messages=[])
    with pytest.raises(ValidationError) as error:
        StringsNotAllowed("abc", "123", match_on_substrings=True)(None, mock_field)

    assert str(error.value) == expected_error
    assert mock_field.error_summary_messages == expected_error_summary_messages


def test_string_cannot_contain_string_with_custom_error_message():
    mock_field = _gen_mock_field("abc", error_summary_messages=[])
    with pytest.raises(ValidationError) as error:
        StringsNotAllowed(
            "abc", "123", message="No sequences please", error_summary_message="No sequences in %s please"
        )(None, mock_field)

    assert str(error.value) == "No sequences please"
    assert mock_field.error_summary_messages == ["No sequences in %s please"]

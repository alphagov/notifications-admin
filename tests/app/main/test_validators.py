from unittest.mock import Mock

import pytest
from wtforms import ValidationError

from app.main.forms import RegisterUserForm, ServiceSmsSenderForm
from app.main.validators import (
    MustContainAlphanumericCharacters,
    NoCommasInPlaceHolders,
    OnlySMSCharacters,
    ValidGovEmail,
)


@pytest.mark.parametrize('password', [
    'govuknotify', '11111111', 'kittykat', 'blackbox'
])
def test_should_raise_validation_error_for_password(
    client_request,
    mock_get_user_by_email,
    password,
):
    form = RegisterUserForm()
    form.name.data = 'test'
    form.email_address.data = 'teset@example.gov.uk'
    form.mobile_number.data = '441231231231'
    form.password.data = password

    form.validate()
    assert 'Choose a password that’s harder to guess' in form.errors['password']


def test_valid_email_not_in_valid_domains(
    client_request,
    mock_get_organisations,
):
    form = RegisterUserForm(email_address="test@test.com", mobile_number='441231231231')
    assert not form.validate()
    assert "Enter a public sector email address" in form.errors['email_address'][0]


def test_valid_email_in_valid_domains(
    client_request,
):
    form = RegisterUserForm(
        name="test",
        email_address="test@my.gov.uk",
        mobile_number='4407888999111',
        password='an uncommon password')
    form.validate()
    assert form.errors == {}


def test_invalid_email_address_error_message(
    client_request,
    mock_get_organisations,
):
    form = RegisterUserForm(
        name="test",
        email_address="test.com",
        mobile_number='4407888999111',
        password='1234567890')
    assert not form.validate()

    form = RegisterUserForm(
        name="test",
        email_address="test.com",
        mobile_number='4407888999111',
        password='1234567890')
    assert not form.validate()


def _gen_mock_field(x):
    return Mock(data=x)


@pytest.mark.parametrize("email", [
    'test@gov.uk',
    'test@GOV.UK',
    'test@gov.uK',
    'test@test.test.gov.uk',
    'test@test.gov.uk',
    'test@nhs.uk',
    'test@gov.nhs.uk',
    'test@nhs.net',
    'test@gov.nhs.net',
    'test@nhs.scot',
    'test@police.uk',
    'test@gov.police.uk',
    'test@GOV.PoliCe.uk',
    'test@cjsm.net',
    'test@example.ac.uk',
    'test@example.sch.uk',
])
def test_valid_list_of_white_list_email_domains(
    client_request,
    email,
):
    email_domain_validators = ValidGovEmail()
    email_domain_validators(None, _gen_mock_field(email))


@pytest.mark.parametrize("email", [
    'test@ukgov.uk',
    'test@gov.uk.uk',
    'test@gov.test.uk',
    'test@ukmod.uk',
    'test@mod.uk.uk',
    'test@mod.test.uk',
    'test@ukddc-mod.org',
    'test@ddc-mod.org.uk',
    'test@ddc-mod.uk.org',
    'test@ukgov.scot',
    'test@gov.scot.uk',
    'test@gov.test.scot',
    'test@ukparliament.uk',
    'test@parliament.uk.uk',
    'test@parliament.test.uk',
    'test@uknhs.uk',
    'test@nhs.uk.uk',
    'test@uknhs.net',
    'test@nhs.net.uk',
    'test@nhs.test.net',
    'test@ukpolice.uk',
    'test@police.uk.uk',
    'test@police.test.uk',
    'test@ucds.com',
    'test@123bl.uk',
])
def test_invalid_list_of_white_list_email_domains(
    client_request,
    email,
    mock_get_organisations,
):
    email_domain_validators = ValidGovEmail()
    with pytest.raises(ValidationError):
        email_domain_validators(None, _gen_mock_field(email))


def test_for_commas_in_placeholders(
    client_request,
):
    with pytest.raises(ValidationError) as error:
        NoCommasInPlaceHolders()(None, _gen_mock_field('Hello ((name,date))'))
    assert str(error.value) == 'You cannot put commas between double brackets'
    NoCommasInPlaceHolders()(None, _gen_mock_field('Hello ((name))'))


@pytest.mark.parametrize('msg', ['The quick brown fox', 'Thé “quick” bröwn fox\u200B'])
def test_sms_character_validation(client_request, msg):
    OnlySMSCharacters(template_type='sms')(None, _gen_mock_field(msg))


@pytest.mark.parametrize('data, err_msg', [
    (
        '∆ abc 📲 def 📵 ghi',
        (
            'You cannot use ∆, 📲 or 📵 in text messages. '
            'They will not show up properly on everyone’s phones.'
        )
    ),
    (
        '📵',
        (
            'You cannot use 📵 in text messages. '
            'It will not show up properly on everyone’s phones.'
        )
    ),
])
def test_non_sms_character_validation(data, err_msg, client_request):
    with pytest.raises(ValidationError) as error:
        OnlySMSCharacters(template_type='sms')(None, _gen_mock_field(data))

    assert str(error.value) == err_msg


@pytest.mark.parametrize("string", [".", "A.", ".8...."])
def test_if_string_does_not_contain_alphanumeric_characters_raises(string):
    with pytest.raises(ValidationError) as error:
        MustContainAlphanumericCharacters()(None, _gen_mock_field(string))

    assert str(error.value) == "Must include at least two alphanumeric characters"


@pytest.mark.parametrize("string", [".A8", "AB.", ".42...."])
def test_if_string_contains_alphanumeric_characters_does_not_raise(string):
    MustContainAlphanumericCharacters()(None, _gen_mock_field(string))


@pytest.mark.parametrize(
    "sms_sender,error_expected,error_message",
    [
        ('', True, 'Cannot be empty'),
        ('22', True, 'Enter 3 characters or more'),
        ('333', False, None),
        ('elevenchars', False, None),  # 11 chars
        ('twelvecharas', True, 'Enter 11 characters or fewer'),  # 12 chars
        ('###', True, 'Use letters and numbers only'),
        ('00111222333', True, 'Cannot start with 00'),
        ('UK_GOV', False, None),  # Underscores are allowed
        ('UK.GOV', False, None),  # Full stops are allowed
        ("'UC'", False, None),  # Straight single quotes are allowed
    ]
)
def test_sms_sender_form_validation(
    client_request,
    mock_get_user_by_email,
    sms_sender,
    error_expected,
    error_message
):
    form = ServiceSmsSenderForm()
    form.sms_sender.data = sms_sender

    form.validate()

    if error_expected:
        assert form.errors
        assert error_message == form.errors['sms_sender'][0]
    else:
        assert not form.errors

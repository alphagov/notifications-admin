import pytest
from app.main.forms import RegisterUserForm
from app.main.validators import ValidEmailDomainRegex
from wtforms import ValidationError
from unittest.mock import Mock


def test_should_raise_validation_error_for_password(app_, mock_get_user_by_email):
    form = RegisterUserForm()
    form.name.data = 'test'
    form.email_address.data = 'teset@example.gov.uk'
    form.mobile_number.data = '441231231231'
    form.password.data = 'password1234'

    form.validate()
    assert 'That password is blacklisted, too common' in form.errors['password']


def test_valid_email_not_in_valid_domains(app_):
    with app_.test_request_context():
        form = RegisterUserForm(email_address="test@test.com", mobile_number='441231231231')
        assert not form.validate()
        assert "Enter a central government email address" in form.errors['email_address'][0]


def test_valid_email_in_valid_domains(app_):
    with app_.test_request_context():
        form = RegisterUserForm(
            name="test",
            email_address="test@my.gov.uk",
            mobile_number='4407888999111',
            password='1234567890')
        form.validate()
        assert form.errors == {}


def test_invalid_email_address_error_message(app_):
    with app_.test_request_context():
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
    'test@test.test.gov.uk',
    'test@test.gov.uk',
    'test@mod.uk',
    'test@ddc-mod.org',
    'test@test.ddc-mod.org',
    'test@gov.scot',
    'test@test.gov.scot',
    'test@parliament.uk',
    'test@gov.parliament.uk',
    'test@nhs.uk',
    'test@gov.nhs.uk',
    'test@nhs.net',
    'test@gov.nhs.net',
    'test@police.uk',
    'test@gov.police.uk'
])
def test_valid_list_of_white_list_email_domains(app_, email):
    with app_.test_request_context():
        email_domain_validators = ValidEmailDomainRegex()
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
    'test@police.test.uk'
])
def test_invalid_list_of_white_list_email_domains(app_, email):
    with app_.test_request_context():
        email_domain_validators = ValidEmailDomainRegex()
        with pytest.raises(ValidationError):
            email_domain_validators(None, _gen_mock_field(email))

import pytest
from app.main.forms import RegisterUserForm, ServiceSmsSender
from app.main.validators import ValidGovEmail, NoCommasInPlaceHolders
from wtforms import ValidationError
from unittest.mock import Mock


@pytest.mark.parametrize('password', [
    'govuknotify', '11111111', 'kittykat', 'evangeli'
])
def test_should_raise_validation_error_for_password(app_, mock_get_user_by_email, password):
    with app_.test_request_context():
        form = RegisterUserForm()
        form.name.data = 'test'
        form.email_address.data = 'teset@example.gov.uk'
        form.mobile_number.data = '441231231231'
        form.password.data = password

        form.validate()
        assert 'Choose a password that’s harder to guess' in form.errors['password']


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
            password='an uncommon password')
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
    'test@GOV.UK',
    'test@gov.uK',
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
    'test@gov.police.uk',
    'test@GOV.PoliCe.uk',
    'test@ucds.email',
    'test@naturalengland.org.uk',
    'test@hmcts.net',
])
def test_valid_list_of_white_list_email_domains(app_, email):
    with app_.test_request_context():
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
    'test@ucds.com'
])
def test_invalid_list_of_white_list_email_domains(app_, email):
    with app_.test_request_context():
        email_domain_validators = ValidGovEmail()
        with pytest.raises(ValidationError):
            email_domain_validators(None, _gen_mock_field(email))


def test_for_commas_in_placeholders(app_):
    with app_.test_request_context():
        with pytest.raises(ValidationError) as error:
            NoCommasInPlaceHolders()(None, _gen_mock_field('Hello ((name,date))'))
        assert str(error.value) == 'You can’t have commas in your fields'
        NoCommasInPlaceHolders()(None, _gen_mock_field('Hello ((name))'))


def test_sms_sender_form_validation(app_, mock_get_user_by_email):
    with app_.test_request_context():
        form = ServiceSmsSender()

        form.sms_sender.data = 'elevenchars'
        form.validate()
        assert not form.errors

        form.sms_sender.data = ''
        form.validate()
        assert not form.errors

        form.sms_sender.data = 'morethanelevenchars'
        form.validate()
        assert "Enter fewer than 11 characters" == form.errors['sms_sender'][0]

        form.sms_sender.data = '###########'
        form.validate()
        assert 'Use letters and numbers only' == form.errors['sms_sender'][0]

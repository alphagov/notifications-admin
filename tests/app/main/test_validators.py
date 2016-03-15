from app.main.dao import users_dao
from app.main.forms import RegisterUserForm


def test_should_raise_validation_error_for_password(app_, mock_get_user_by_email):
    with app_.test_request_context():
        form = RegisterUserForm()
        form.name.data = 'test'
        form.email_address.data = 'teset@gov.uk'
        form.mobile_number.data = '+441231231231'
        form.password.data = 'password1234'

        form.validate()
        assert 'That password is blacklisted, too common' in form.errors['password']


def test_valid_email_not_in_valid_domains(app_):
    with app_.test_request_context():
        form = RegisterUserForm(email_address="test@test.com", mobile_number='+441231231231')
        assert not form.validate()
        assert "Enter a central government email address" in form.errors['email_address']


def test_valid_email_in_valid_domains(app_):
    with app_.test_request_context():
        form = RegisterUserForm(
            name="test",
            email_address="test@gov.uk",
            mobile_number='+4407888999111',
            password='1234567890')
        assert form.validate()


def test_invalid_email_address_error_message(app_):
    with app_.test_request_context():
        form = RegisterUserForm(
            name="test",
            email_address="test.com",
            mobile_number='+4407888999111',
            password='1234567890')
        assert not form.validate()

        form = RegisterUserForm(
            name="test",
            email_address="test.com",
            mobile_number='+4407888999111',
            password='1234567890')
        assert not form.validate()

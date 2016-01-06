from pytest import fail

from app.main.forms import RegisterUserForm


def test_should_raise_validation_error_for_password(notifications_admin):
    form = RegisterUserForm([], [])
    form.name.data = 'test'
    form.email_address.data = 'teset@example.gov.uk'
    form.mobile_number.data = '+441231231231'
    form.password.data = 'password1234'

    form.validate()
    assert 'That password is blacklisted, too common' in form.errors['password']

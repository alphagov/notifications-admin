import pytest
from app.main.forms import get_placeholder_form_instance
from wtforms import Label


def test_form_class_not_mutated(app_):

    with app_.test_request_context(
        method='POST',
        data={'placeholder_value': ''}
    ) as req:
        form1 = get_placeholder_form_instance('name', {}, optional_placeholder=False)
        form2 = get_placeholder_form_instance('city', {}, optional_placeholder=True)

        assert not form1.validate_on_submit()
        assert form2.validate_on_submit()

        assert str(form1.placeholder_value.label) == '<label for="placeholder_value">name</label>'
        assert str(form2.placeholder_value.label) == '<label for="placeholder_value">city</label>'


@pytest.mark.parametrize('service_can_send_international_sms, placeholder_name, value, expected_error', [

    (False, 'email address', '', 'Can’t be empty'),
    (False, 'email address', '12345', 'Enter a valid email address'),
    (False, 'email address', 'test@example.com', None),
    (False, 'email address', 'test@example.gov.uk', None),

    (False, 'phone number', '', 'Can’t be empty'),
    (False, 'phone number', '+1-2345-678890', 'Not a UK mobile number'),
    (False, 'phone number', '07900900123', None),
    (False, 'phone number', '+44(0)7900 900-123', None),

    (True, 'phone number', '+123', 'Not enough digits'),
    (True, 'phone number', '+44(0)7900 900-123', None),
    (True, 'phone number', '+1-2345-678890', None),

    (False, 'anything else', '', 'Can’t be empty'),

])
def test_validates_recipients(
    app_,
    placeholder_name,
    value,
    service_can_send_international_sms,
    expected_error,
):
    with app_.test_request_context(
        method='POST',
        data={'placeholder_value': value}
    ):
        form = get_placeholder_form_instance(
            placeholder_name,
            {},
            allow_international_phone_numbers=service_can_send_international_sms,
        )

        if expected_error:
            assert not form.validate_on_submit()
            assert form.placeholder_value.errors[0] == expected_error
        else:
            assert form.validate_on_submit()

import pytest
from wtforms import Form
from app.main.forms import UKMobileNumber


class FormExample(Form):
    phone_number = UKMobileNumber()

invalid_phone_numbers = sum([
    [
        (phone_number, error) for phone_number in group
    ] for error, group in [
        ('Too many digits', (
            '0712345678910',
            '0044712345678910',
            '0044712345678910',
            '+44 (0)7123 456 789 10',
        )),
        ('Not enough digits', (
            '0712345678',
            '004471234567',
            '00447123456',
            '+44 (0)7123 456 78',
        )),
        ('Must be a UK mobile number (eg 07700 900460)', (
            '08081 570364',
            '+44 8081 570364',
            '0117 496 0860',
            '+44 117 496 0860',
            '020 7946 0991',
            '+44 20 7946 0991',
            '71234567890',
        )),
        ('Must not contain letters or symbols', (
            '07890x32109',
            '07123 456789...',
            '07123 ☟☜⬇⬆☞☝',
            '07123☟☜⬇⬆☞☝',
            '07";DROP TABLE;"',
            '+44 07ab cde fgh',
        ))
    ]
], [])

valid_phone_numbers = [
    '07123456789',
    '07123 456789',
    '07123-456-789',
    '00447123456789',
    '00 44 7123456789',
    '+447123456789',
    '+44 7123 456 789',
    '+44 (0)7123 456 789'
]


@pytest.mark.parametrize("phone_number", valid_phone_numbers)
def test_phone_number_accepts_valid_values(phone_number):
    form = FormExample(phone_number=phone_number)
    form.validate()
    assert form.errors == {}


@pytest.mark.parametrize("phone_number, error_message", invalid_phone_numbers)
def test_phone_number_rejects_invalid_values(phone_number, error_message):
    form = FormExample(phone_number=phone_number)
    form.validate()
    assert form.phone_number.errors[0] == error_message


@pytest.mark.parametrize("phone_number", valid_phone_numbers)
def test_phone_number_outputs_in_correct_format(phone_number):
    form = FormExample(phone_number=phone_number)
    form.validate()
    assert form.phone_number.data == '+447123456789'

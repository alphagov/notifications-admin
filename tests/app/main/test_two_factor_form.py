import pytest

from app import user_api_client
from app.main.forms import TwoFactorForm
from tests.conftest import (
    mock_check_verify_code,
    mock_check_verify_code_code_expired,
    mock_check_verify_code_code_not_found,
)


def _check_code(code):
    return user_api_client.check_verify_code('1', code, "sms")


@pytest.mark.parametrize('post_data', [
    {'sms_code': '12345'},
    {'sms_code': ' 12345 '},
])
def test_form_is_valid_returns_no_errors(
    app_,
    mock_check_verify_code,
    post_data,
):
    with app_.test_request_context(method='POST', data=post_data):
        form = TwoFactorForm(_check_code)
        assert form.validate() is True
        assert form.errors == {}


@pytest.mark.parametrize('mock, post_data, expected_error', (
    (
        mock_check_verify_code,
        {'sms_code': '1234'},
        'Not enough numbers',
    ),
    (
        mock_check_verify_code,
        {'sms_code': '123456'},
        'Too many numbers',
    ),
    (
        mock_check_verify_code,
        {},
        'Cannot be empty',
    ),
    (
        mock_check_verify_code,
        {'sms_code': '12E45'},
        'Numbers only',
    ),
    (
        mock_check_verify_code_code_expired,
        {'sms_code': '99999'},
        'Code has expired',
    ),
    (
        mock_check_verify_code_code_not_found,
        {'sms_code': '99999'},
        'Code not found',
    ),
))
def test_returns_errors_when_code_is_too_short(
    app_,
    mocker,
    mock,
    post_data,
    expected_error,
):
    mock(mocker)
    with app_.test_request_context(method='POST', data=post_data):
        form = TwoFactorForm(_check_code)
        assert form.validate() is False
        assert form.errors == {'sms_code': [expected_error]}

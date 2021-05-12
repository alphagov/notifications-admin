import pytest

from app import user_api_client
from app.main.forms import TwoFactorForm


def _check_code(code):
    return user_api_client.check_verify_code('1', code, "sms")


@pytest.mark.parametrize('post_data', [
    {'sms_code': '12345'},
    {'sms_code': ' 12345 '},
    {'sms_code': '12 34 5'},
    {'sms_code': '1-23-45'},
])
def test_form_is_valid_returns_no_errors(
    notify_admin,
    mock_check_verify_code,
    post_data,
):
    with notify_admin.test_request_context(method='POST', data=post_data):
        form = TwoFactorForm(_check_code)
        assert form.validate() is True
        assert form.errors == {}
    mock_check_verify_code.assert_called_once_with('1', '12345', 'sms')


@pytest.mark.parametrize('post_data, expected_error', (
    (
        {'sms_code': '1234'},
        'Not enough numbers',
    ),
    (
        {'sms_code': '123456'},
        'Too many numbers',
    ),
    (
        {},
        'Cannot be empty',
    ),
    (
        {'sms_code': '12E45'},
        'Numbers only',
    ),
    (
        {'sms_code': ' ! 2 3 4 5'},
        'Numbers only',
    ),
))
def test_check_verify_code_returns_errors(
    notify_admin,
    post_data,
    expected_error,
    mock_check_verify_code,
):
    with notify_admin.test_request_context(method='POST', data=post_data):
        form = TwoFactorForm(_check_code)
        assert form.validate() is False
        assert form.errors == {'sms_code': [expected_error]}


def test_check_verify_code_returns_error_when_code_has_expired(
    notify_admin,
    mock_check_verify_code_code_expired,
):
    with notify_admin.test_request_context(method='POST', data={'sms_code': '99999'}):
        form = TwoFactorForm(_check_code)
        assert form.validate() is False
        assert form.errors == {'sms_code': ['Code has expired']}


def test_check_verify_code_returns_error_when_code_was_not_found(
    notify_admin,
    mock_check_verify_code_code_not_found,
):
    with notify_admin.test_request_context(method='POST', data={'sms_code': '99999'}):
        form = TwoFactorForm(_check_code)
        assert form.validate() is False
        assert form.errors == {'sms_code': ['Code not found']}

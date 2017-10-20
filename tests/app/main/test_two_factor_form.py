from app.main.forms import TwoFactorForm
from app import user_api_client


def test_form_is_valid_returns_no_errors(
    app_,
    mock_check_verify_code,
):
    with app_.test_request_context(
        method='POST',
        data={'sms_code': '12345'}
    ):
        def _check_code(code):
            return user_api_client.check_verify_code('1', code, "sms")
        form = TwoFactorForm(_check_code)
        assert form.validate() is True
        assert len(form.errors) == 0


def test_returns_errors_when_code_is_too_short(
    app_,
    mock_check_verify_code,
):
    with app_.test_request_context(
        method='POST',
        data={'sms_code': '145'}
    ):
        def _check_code(code):
            return user_api_client.check_verify_code('1', code, "sms")
        form = TwoFactorForm(_check_code)
        assert form.validate() is False
        assert len(form.errors) == 1
        assert set(form.errors) == set({'sms_code': ['Code not found', 'Code does not match']})


def test_returns_errors_when_code_is_missing(
    app_,
    mock_check_verify_code,
):
    with app_.test_request_context(
        method='POST',
        data={}
    ):
        def _check_code(code):
            return user_api_client.check_verify_code('1', code, "sms")
        form = TwoFactorForm(_check_code)
        assert form.validate() is False
        assert len(form.errors) == 1
        assert set(form.errors) == set({'sms_code': ['Code must not be empty']})


def test_returns_errors_when_code_contains_letters(
    app_,
    mock_check_verify_code,
):
    with app_.test_request_context(
        method='POST',
        data={'sms_code': 'asdfg'}
    ):
        def _check_code(code):
            return user_api_client.check_verify_code('1', code, "sms")
        form = TwoFactorForm(_check_code)
        assert form.validate() is False
        assert len(form.errors) == 1
        assert set(form.errors) == set({'sms_code': ['Code not found', 'Code does not match']})


def test_should_return_errors_when_code_is_expired(
    app_,
    mock_check_verify_code_code_expired,
):
    with app_.test_request_context(
        method='POST',
        data={'sms_code': '23456'}
    ):
        def _check_code(code):
            return user_api_client.check_verify_code('1', code, "sms")
        form = TwoFactorForm(_check_code)
        assert form.validate() is False
        errors = form.errors
        assert len(errors) == 1
        assert errors == {'sms_code': ['Code has expired']}

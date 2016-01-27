from datetime import datetime, timedelta

from app.main.forms import TwoFactorForm
from app.main.dao import users_dao
from tests import create_test_user


def test_form_is_valid_returns_no_errors(app_, mock_check_verify_code):
    with app_.test_request_context(method='POST',
                                   data={'sms_code': '12345'}) as req:
        def _check_code(code):
            return users_dao.check_verify_code('1', code, "sms")
        form = TwoFactorForm(_check_code)
        assert form.validate() is True
        assert len(form.errors) == 0


def test_returns_errors_when_code_is_too_short(app_, mock_check_verify_code):
    with app_.test_request_context(method='POST',
                                   data={'sms_code': '145'}) as req:
        def _check_code(code):
            return users_dao.check_verify_code('1', code, "sms")
        form = TwoFactorForm(_check_code)
        assert form.validate() is False
        assert len(form.errors) == 1
        assert set(form.errors) == set({'sms_code': ['Code must be 5 digits', 'Code does not match']})


def test_returns_errors_when_code_is_missing(app_, mock_check_verify_code):
    with app_.test_request_context(method='POST',
                                   data={}) as req:
        def _check_code(code):
            return users_dao.check_verify_code('1', code, "sms")
        form = TwoFactorForm(_check_code)
        assert form.validate() is False
        assert len(form.errors) == 1
        assert set(form.errors) == set({'sms_code': ['Code must not be empty']})


def test_returns_errors_when_code_contains_letters(app_, mock_check_verify_code):
    with app_.test_request_context(method='POST',
                                   data={'sms_code': 'asdfg'}) as req:
        def _check_code(code):
            return users_dao.check_verify_code('1', code, "sms")
        form = TwoFactorForm(_check_code)
        assert form.validate() is False
        assert len(form.errors) == 1
        assert set(form.errors) == set({'sms_code': ['Code must be 5 digits', 'Code does not match']})


def test_should_return_errors_when_code_is_expired(app_,
                                                   mock_check_verify_code_code_expired):
    with app_.test_request_context(method='POST',
                                   data={'sms_code': '23456'}) as req:
        def _check_code(code):
            return users_dao.check_verify_code('1', code, "sms")
        form = TwoFactorForm(_check_code)
        assert form.validate() is False
        errors = form.errors
        assert len(errors) == 1
        assert errors == {'sms_code': ['Code has expired']}

from datetime import datetime, timedelta
from app.main.forms import VerifyForm
from app.main.dao import users_dao
from tests import create_test_user


def test_form_should_have_error_when_code_is_not_valid(app_,
                                                       mock_check_verify_code):
    with app_.test_request_context(method='POST',
                                   data={'sms_code': '12345aa', 'email_code': 'abcde'}) as req:

        def _check_code(code, code_type):
            return users_dao.check_verify_code('1', code, code_type)

        form = VerifyForm(_check_code)
        assert form.validate() is False
        errors = form.errors
        assert len(errors) == 2
        expected = {'email_code': ['Code must be 5 digits', 'Code does not match'],
                    'sms_code': ['Code does not match', 'Code must be 5 digits']}
        assert 'sms_code' in errors
        assert set(errors) == set(expected)


def test_should_return_errors_when_code_missing(app_,
                                                mock_check_verify_code):
    with app_.test_request_context(method='POST',
                                   data={}) as req:

        def _check_code(code, code_type):
            return users_dao.check_verify_code('1', code, code_type)

        form = VerifyForm(_check_code)
        assert form.validate() is False
        errors = form.errors
        expected = {'sms_code': ['SMS code can not be empty'],
                    'email_code': ['Email code can not be empty']}
        assert len(errors) == 2
        assert set(errors) == set(expected)


def test_should_return_errors_when_code_is_too_short(app_,
                                                     mock_check_verify_code):
    with app_.test_request_context(method='POST',
                                   data={'sms_code': '123', 'email_code': '123'}) as req:

        def _check_code(code, code_type):
            return users_dao.check_verify_code('1', code, code_type)

        form = VerifyForm(_check_code)
        assert form.validate() is False
        errors = form.errors
        expected = {'sms_code': ['Code must be 5 digits', 'Code does not match'],
                    'email_code': ['Code must be 5 digits', 'Code does not match']}
        assert len(errors) == 2
        assert set(errors) == set(expected)


def test_should_return_errors_when_code_does_not_match(app_,
                                                       mock_check_verify_code_code_not_found):
    with app_.test_request_context(method='POST',
                                   data={'sms_code': '34567', 'email_code': '34567'}) as req:

        def _check_code(code, code_type):
            return users_dao.check_verify_code('1', code, code_type)

        form = VerifyForm(_check_code)
        assert form.validate() is False
        errors = form.errors
        expected = {'sms_code': ['Code not found'],
                    'email_code': ['Code not found']}
        assert len(errors) == 2
        assert set(errors) == set(expected)


def test_should_return_errors_when_code_is_expired(app_,
                                                   mock_check_verify_code_code_expired):
    with app_.test_request_context(method='POST',
                                   data={'sms_code': '23456',
                                         'email_code': '23456'}) as req:

        def _check_code(code, code_type):
            return users_dao.check_verify_code('1', code, code_type)

        form = VerifyForm(_check_code)
        assert form.validate() is False
        errors = form.errors
        expected = {'sms_code': ['Code has expired'],
                    'email_code': ['Code has expired']}
        assert len(errors) == 2
        assert set(errors) == set(expected)

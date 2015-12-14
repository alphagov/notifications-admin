from datetime import datetime, timedelta
from app.main.dao import verify_codes_dao
from app.main.forms import VerifyForm
from tests.app.main import create_test_user


def test_form_should_have_error_when_code_is_not_valid(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context(method='POST',
                                                  data={'sms_code': '12345aa', 'email_code': 'abcde'}) as req:
        user = set_up_test_data()
        req.session['user_id'] = user.id
        form = VerifyForm(req.request.form)
        assert form.validate() is False
        errors = form.errors
        assert len(errors) == 2
        expected = {'email_code': ['Code must be 5 digits', 'Code does not match'],
                    'sms_code': ['Code does not match', 'Code must be 5 digits']}
        assert 'sms_code' in errors
        assert set(errors) == set(expected)


def test_should_return_errors_when_code_missing(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context(method='POST',
                                                  data={}) as req:
        user = set_up_test_data()
        req.session['user_id'] = user.id
        form = VerifyForm(req.request.form)
        assert form.validate() is False
        errors = form.errors
        expected = {'sms_code': ['SMS code can not be empty'],
                    'email_code': ['Email code can not be empty']}
        assert len(errors) == 2
        assert set(errors) == set(expected)


def test_should_return_errors_when_code_is_too_short(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context(method='POST',
                                                  data={'sms_code': '123', 'email_code': '123'}) as req:
        user = set_up_test_data()
        req.session['user_id'] = user.id
        form = VerifyForm(req.request.form)
        assert form.validate() is False
        errors = form.errors
        expected = {'sms_code': ['Code must be 5 digits', 'Code does not match'],
                    'email_code': ['Code must be 5 digits', 'Code does not match']}
        assert len(errors) == 2
        assert set(errors) == set(expected)


def test_should_return_errors_when_code_does_not_match(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context(method='POST',
                                                  data={'sms_code': '23456', 'email_code': '23456'}) as req:
        user = set_up_test_data()
        req.session['user_id'] = user.id
        form = VerifyForm(req.request.form)
        assert form.validate() is False
        errors = form.errors
        expected = {'sms_code': ['Code does not match'],
                    'email_code': ['Code does not match']}
        assert len(errors) == 2
        assert set(errors) == set(expected)


def test_should_return_errors_when_code_is_expired(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context(method='POST',
                                                  data={'sms_code': '23456',
                                                        'email_code': '23456'}) as req:
        user = set_up_test_data()
        req.session['user_id'] = user.id
        verify_codes_dao.add_code_with_expiry(user_id=user.id,
                                              code='23456',
                                              code_type='sms',
                                              expiry=datetime.now() + timedelta(hours=-2))

        verify_codes_dao.add_code_with_expiry(user_id=user.id,
                                              code='23456',
                                              code_type='email',
                                              expiry=datetime.now() + timedelta(hours=-2))
        req.session['user_id'] = user.id
        form = VerifyForm(req.request.form)
        assert form.validate() is False
        errors = form.errors
        expected = set({'sms_code': ['Code has expired'],
                        'email_code': ['Code has exprired']})
        assert len(errors) == 2
        assert set(errors) == expected


def set_up_test_data():
    user = create_test_user()
    verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='email')
    verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
    return user

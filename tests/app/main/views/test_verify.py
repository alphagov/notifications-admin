from datetime import datetime, timedelta

from flask import json

from app.main.dao import users_dao, verify_codes_dao
from tests.app.main import create_test_user


def test_should_return_verify_template(notifications_admin, notifications_admin_db, notify_db_session):
    response = notifications_admin.test_client().get('/verify')
    assert response.status_code == 200
    assert 'Activate your account' in response.get_data(as_text=True)


def test_should_redirect_to_add_service_when_code_are_correct(notifications_admin,
                                                              notifications_admin_db,
                                                              notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
        verify_codes_dao.add_code(user_id=user.id, code='23456', code_type='email')
        response = client.post('/verify',
                               data={'sms_code': '12345',
                                     'email_code': '23456'})
        assert response.status_code == 302
        assert response.location == 'http://localhost/add-service'


def test_should_activate_user_after_verify(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
        verify_codes_dao.add_code(user_id=user.id, code='23456', code_type='email')
        client.post('/verify',
                    data={'sms_code': '12345',
                          'email_code': '23456'})

        after_verify = users_dao.get_user_by_id(user.id)
        assert after_verify.state == 'active'


def test_should_return_400_when_codes_are_wrong(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='23345', code_type='sms')
        verify_codes_dao.add_code(user_id=user.id, code='98456', code_type='email')
        response = client.post('/verify',
                               data={'sms_code': '12345',
                                     'email_code': '23456'})
        assert response.status_code == 400
        expected = {'sms_code': ['Code must be 5 digits', 'Code does not match'],
                        'email_code': ['Code must be 5 digits', 'Code does not match']}
        errors = json.loads(response.get_data(as_text=True))
        assert len(errors) == 2
        assert 'sms_code' in errors
        assert errors['sms_code'] == expected['sms_code']
        assert 'email_code' in errors
        assert set(errors['email_code']) in set(expected['email_code'])


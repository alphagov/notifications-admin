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


def test_should_return_400_when_sms_code_is_wrong(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
        verify_codes_dao.add_code(user_id=user.id, code='23456', code_type='email')
        response = client.post('/verify',
                               data={'sms_code': '98765',
                                     'email_code': '23456'})
        assert response.status_code == 400
        assert {'sms_code': ['Code does not match']} == json.loads(response.get_data(as_text=True))


def test_should_return_400_when_email_code_is_wrong(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
        verify_codes_dao.add_code(user_id=user.id, code='98456', code_type='email')
        response = client.post('/verify',
                               data={'sms_code': '12345',
                                     'email_code': '23456'})
        assert response.status_code == 400
        assert {'email_code': ['Code does not match']} == json.loads(response.get_data(as_text=True))


def test_should_return_400_when_sms_code_is_missing(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
        verify_codes_dao.add_code(user_id=user.id, code='98456', code_type='email')
        response = client.post('/verify',
                               data={'email_code': '98456'})
        assert response.status_code == 400
        assert {'sms_code': ['SMS code can not be empty']} == json.loads(response.get_data(as_text=True))


def test_should_return_400_when_email_code_is_missing(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='23456', code_type='email')
        verify_codes_dao.add_code(user_id=user.id, code='23456', code_type='sms')
        response = client.post('/verify',
                               data={'sms_code': '23456'})
        assert response.status_code == 400
        assert {'email_code': ['Email code can not be empty']} == json.loads(response.get_data(as_text=True))


def test_should_return_400_when_email_code_has_letter(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='23456', code_type='email')
        verify_codes_dao.add_code(user_id=user.id, code='23456', code_type='sms')
        response = client.post('/verify',
                               data={'sms_code': '23456',
                                     'email_code': 'abcde'})
        assert response.status_code == 400
        data = json.loads(response.get_data(as_text=True))
        expected = {'email_code': ['Code does not match', 'Code must be 5 digits']}
        assert len(data.keys()) == 1
        assert 'email_code' in data
        assert data['email_code'].sort() == expected['email_code'].sort()


def test_should_return_400_when_sms_code_is_too_short(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='23456', code_type='email')
        verify_codes_dao.add_code(user_id=user.id, code='23456', code_type='sms')
        response = client.post('/verify',
                               data={'sms_code': '2345',
                                     'email_code': '23456'})
        assert response.status_code == 400
        data = json.loads(response.get_data(as_text=True))
        expected = {'sms_code': ['Code must be 5 digits', 'Code does not match']}
        assert len(data.keys()) == 1
        assert 'sms_code' in data
        assert data['sms_code'].sort() == expected['sms_code'].sort()


def test_should_return_302_when_email_code_starts_with_zero(notifications_admin,
                                                            notifications_admin_db,
                                                            notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='23456', code_type='sms')
        verify_codes_dao.add_code(user_id=user.id, code='09765', code_type='email')
        response = client.post('/verify',
                               data={'sms_code': '23456',
                                     'email_code': '09765'})
        assert response.status_code == 302
        assert response.location == 'http://localhost/add-service'


def test_should_return_400_when_verify_code_has_expired(notifications_admin,
                                                        notifications_admin_db,
                                                        notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code_with_expiry(user_id=user.id,
                                              code='23456',
                                              code_type='email',
                                              expiry=datetime.now() + timedelta(hours=-2))
        verify_codes_dao.add_code_with_expiry(user_id=user.id,
                                              code='23456',
                                              code_type='sms',
                                              expiry=datetime.now() + timedelta(hours=-2))
        response = client.post('/verify',
                               data={'sms_code': '23456',
                                     'email_code': '23456'})
        assert response.status_code == 400
        data = json.loads(response.get_data(as_text=True))
        expected = {'sms_code': ['Code has expired'],
                    'email_code': ['Code has expired']}
        assert len(data.keys()) == 2
        assert 'sms_code' in data
        assert data['sms_code'].sort() == expected['sms_code'].sort()
        assert 'email_code' in data
        assert data['email_code'].sort() == expected['email_code'].sort()

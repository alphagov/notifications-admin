from flask import json

from app.main.dao import verify_codes_dao
from tests.app.main import create_test_user


def test_should_render_two_factor_page(notifications_admin, notifications_admin_db, notify_db_session):
    response = notifications_admin.test_client().get('/two-factor')
    assert response.status_code == 200
    assert '''We've sent you a text message with a verification code.''' in response.get_data(as_text=True)


def test_should_login_user_and_redirect_to_dashboard(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
        response = client.post('/two-factor',
                               data={'sms_code': '12345'})

        assert response.status_code == 302
        assert response.location == 'http://localhost/dashboard'


def test_should_return_400_with_sms_code_error_when_sms_code_is_wrong(notifications_admin,
                                                                      notifications_admin_db,
                                                                      notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
        response = client.post('/two-factor',
                               data={'sms_code': '23456'})
        assert response.status_code == 400
        assert {'sms_code': ['Code does not match']} == json.loads(response.get_data(as_text=True))


def test_should_return_400_when_sms_code_is_empty(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
        response = client.post('/two-factor')
        assert response.status_code == 400
        assert {'sms_code': ['Please enter your code']} == json.loads(response.get_data(as_text=True))


def test_should_return_400_when_sms_code_is_too_short(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='23467', code_type='sms')
        response = client.post('/two-factor', data={'sms_code': '2346'})
        assert response.status_code == 400
        data = json.loads(response.get_data(as_text=True))
        assert len(data.keys()) == 1
        assert set(data) == set({'sms_code': ['Code must be 5 digits', 'Code does not match']})

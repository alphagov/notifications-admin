from datetime import datetime

from app.main.dao import users_dao
from app.main.encryption import hashpw
from app.models import User


def test_should_return_verify_template(notifications_admin, notifications_admin_db):
    response = notifications_admin.test_client().get('/verify')
    assert response.status_code == 200
    assert 'Activate your account' in response.get_data(as_text=True)


def test_should_redirect_to_add_service_when_code_are_correct(notifications_admin, notifications_admin_db):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = _create_test_user()
            session['user_id'] = user.id
            session['sms_code'] = hashpw('12345')
            session['email_code'] = hashpw('23456')
        response = client.post('/verify',
                               data={'sms_code': '12345',
                                     'email_code': '23456'})
        assert response.status_code == 302
        assert response.location == 'http://localhost/add-service'


def test_should_activate_user_after_verify(notifications_admin, notifications_admin_db):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = _create_test_user()
            session['user_id'] = user.id
            session['sms_code'] = hashpw('12345')
            session['email_code'] = hashpw('23456')
        client.post('/verify',
                    data={'sms_code': '12345',
                          'email_code': '23456'})

        after_verify = users_dao.get_user_by_id(user.id)
        assert after_verify.state == 'active'


def test_should_return_400_when_sms_code_is_wrong(notifications_admin, notifications_admin_db):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = _create_test_user()
            session['user_id'] = user.id
            session['sms_code'] = hashpw('12345')
            session['email_code'] = hashpw('23456')
        response = client.post('/verify',
                               data={'sms_code': '98765',
                                     'email_code': '23456'})
        assert response.status_code == 400
        assert 'sms_code' in response.get_data(as_text=True)
        assert 'Code does not match' in response.get_data(as_text=True)


def test_should_return_400_when_email_code_is_wrong(notifications_admin, notifications_admin_db):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = _create_test_user()
            session['user_id'] = user.id
            session['sms_code'] = hashpw('12345')
            session['email_code'] = hashpw('98456')
        response = client.post('/verify',
                               data={'sms_code': '12345',
                                     'email_code': '23456'})
        assert response.status_code == 400
        print(response.get_data(as_text=True))
        assert 'email_code' in response.get_data(as_text=True)
        assert 'Code does not match' in response.get_data(as_text=True)


def test_should_return_400_when_sms_code_is_missing(notifications_admin, notifications_admin_db):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = _create_test_user()
            session['user_id'] = user.id
            session['sms_code'] = hashpw('12345')
            session['email_code'] = hashpw('98456')
        response = client.post('/verify',
                               data={'email_code': '23456'})
        assert response.status_code == 400
        assert 'SMS code can not be empty' in response.get_data(as_text=True)


def test_should_return_400_when_email_code_is_missing(notifications_admin, notifications_admin_db):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = _create_test_user()
            session['user_id'] = user.id
            session['sms_code'] = hashpw('23456')
            session['email_code'] = hashpw('23456')
        response = client.post('/verify',
                               data={'sms_code': '23456'})
        assert response.status_code == 400
        assert 'Email code can not be empty' in response.get_data(as_text=True)


def test_should_return_400_when_email_code_has_letter(notifications_admin, notifications_admin_db):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = _create_test_user()
            session['user_id'] = user.id
            session['sms_code'] = hashpw('23456')
            session['email_code'] = hashpw('23456')
        response = client.post('/verify',
                               data={'sms_code': '23456',
                                     'email_code': 'abcde'})
        assert response.status_code == 400
        assert 'Code does not match' in response.get_data(as_text=True)


def test_should_return_302_when_email_code_starts_with_zero(notifications_admin, notifications_admin_db):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = _create_test_user()
            session['user_id'] = user.id
            session['sms_code'] = hashpw('23456')
            session['email_code'] = hashpw('09765')
        response = client.post('/verify',
                               data={'sms_code': '23456',
                                     'email_code': '09765'})
        assert response.status_code == 302
        assert response.location == 'http://localhost/add-service'


def _create_test_user():
    user = User(name='Test User',
                password='somepassword',
                email_address='test@user.gov.uk',
                mobile_number='+441234123412',
                created_at=datetime.now(),
                role_id=1,
                state='pending')
    users_dao.insert_user(user)
    return user

from datetime import datetime

from app.main.dao import users_dao
from app.main.encryption import hashpw
from app.models import User


def test_should_render_two_factor_page(notifications_admin, notifications_admin_db):
    response = notifications_admin.test_client().get('/two-factor')
    assert response.status_code == 200
    assert '''We've sent you a text message with a verification code.''' in response.get_data(as_text=True)


def test_should_login_user_and_redirect_to_dashboard(notifications_admin, notifications_admin_db):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = _create_test_user()
            session['user_id'] = user.id
            session['sms_code'] = hashpw('12345')
        response = client.post('/two-factor',
                               data={'sms_code': '12345'})

        assert response.status_code == 302
        assert response.location == 'http://localhost/dashboard'


def test_should_return_400_with_sms_code_error_when_sms_code_is_wrong(notifications_admin, notifications_admin_db):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = _create_test_user()
            session['user_id'] = user.id
            session['sms_code'] = hashpw('12345')
        response = client.post('/two-factor',
                               data={'sms_code': '23456'})
        assert response.status_code == 400
        assert 'sms_code' in response.get_data(as_text=True)
        assert 'Code does not match' in response.get_data(as_text=True)


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

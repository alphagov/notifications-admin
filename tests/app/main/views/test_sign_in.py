from datetime import datetime

from app.main.dao import users_dao
from app.models import User


def test_render_sign_in_returns_sign_in_template(notifications_admin):
    response = notifications_admin.test_client().get('/sign-in')
    assert response.status_code == 200
    assert 'Sign in' in response.get_data(as_text=True)
    assert 'Email address' in response.get_data(as_text=True)
    assert 'Password' in response.get_data(as_text=True)
    assert 'Forgotten password?' in response.get_data(as_text=True)


def test_process_sign_in_return_2fa_template(notifications_admin, notifications_admin_db):
    user = User(email_address='valid@example.gov.uk',
                password='val1dPassw0rd!',
                mobile_number='+441234123123',
                name='valid',
                created_at=datetime.now(),
                role_id=1)
    users_dao.insert_user(user)
    response = notifications_admin.test_client().post('/sign-in',
                                                      data={'email_address': 'valid@example.gov.uk',
                                                            'password': 'val1dPassw0rd!'})
    assert response.status_code == 302
    assert response.location == 'http://localhost/two-factor'


def test_temp_create_user(notifications_admin, notifications_admin_db):
    response = notifications_admin.test_client().post('/temp-create-users',
                                                      data={'email_address': 'testing@example.gov.uk',
                                                            'password': 'val1dPassw0rd!'})

    assert response.status_code == 302


def test_should_return_locked_out_true_when_user_is_locked(notifications_admin, notifications_admin_db):
    user = User(email_address='valid@example.gov.uk',
                password='val1dPassw0rd!',
                mobile_number='+441234123123',
                name='valid',
                created_at=datetime.now(),
                role_id=1)
    users_dao.insert_user(user)
    for _ in range(10):
        notifications_admin.test_client().post('/sign-in',
                                               data={'email_address': 'valid@example.gov.uk',
                                                     'password': 'whatIsMyPassword!'})

    response = notifications_admin.test_client().post('/sign-in',
                                                      data={'email_address': 'valid@example.gov.uk',
                                                            'password': 'val1dPassw0rd!'})

    assert response.status_code == 401
    assert '"locked_out": true' in response.get_data(as_text=True)

    another_bad_attempt = notifications_admin.test_client().post('/sign-in',
                                                                 data={'email_address': 'valid@example.gov.uk',
                                                                       'password': 'whatIsMyPassword!'})
    assert another_bad_attempt.status_code == 401
    assert '"locked_out": true' in response.get_data(as_text=True)


def test_should_return_active_user_is_false_if_user_is_inactive(notifications_admin, notifications_admin_db):
    user = User(email_address='inactive_user@example.gov.uk',
                password='val1dPassw0rd!',
                mobile_number='+441234123123',
                name='inactive user',
                created_at=datetime.now(),
                role_id=1,
                state='inactive')
    users_dao.insert_user(user)

    response = notifications_admin.test_client().post('/sign-in',
                                                      data={'email_address': 'inactive_user@example.gov.uk',
                                                            'password': 'val1dPassw0rd!'})

    assert response.status_code == 401
    assert '"active_user": false' in response.get_data(as_text=True)


def test_should_return_401_when_user_does_not_exist(notifications_admin, notifications_admin_db):
    response = notifications_admin.test_client().post('/sign-in',
                                                      data={'email_address': 'does_not_exist@gov.uk',
                                                            'password': 'doesNotExist!'})

    assert response.status_code == 401

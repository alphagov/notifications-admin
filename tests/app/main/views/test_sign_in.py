from datetime import datetime

from app.main.dao import users_dao
from app.models import User
from flask import url_for


def test_render_sign_in_returns_sign_in_template(notifications_admin):
    with notifications_admin.test_request_context():
        response = notifications_admin.test_client().get(url_for('main.sign_in'))
    assert response.status_code == 200
    assert 'Sign in' in response.get_data(as_text=True)
    assert 'Email address' in response.get_data(as_text=True)
    assert 'Password' in response.get_data(as_text=True)
    assert 'Forgotten password?' in response.get_data(as_text=True)


def test_process_sign_in_return_2fa_template(notifications_admin, notifications_admin_db, mocker, notify_db_session):
    _set_up_mocker(mocker)
    user = User(email_address='valid@example.gov.uk',
                password='val1dPassw0rd!',
                mobile_number='+441234123123',
                name='valid',
                created_at=datetime.now(),
                role_id=1,
                state='active')
    users_dao.insert_user(user)
    with notifications_admin.test_request_context():
        response = notifications_admin.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'valid@example.gov.uk',
                'password': 'val1dPassw0rd!'})
    assert response.status_code == 302
    assert response.location == 'http://localhost/two-factor'


def test_should_return_locked_out_true_when_user_is_locked(notifications_admin,
                                                           notifications_admin_db,
                                                           notify_db_session):
    user = User(email_address='valid@example.gov.uk',
                password='val1dPassw0rd!',
                mobile_number='+441234123123',
                name='valid',
                created_at=datetime.now(),
                role_id=1,
                state='active')
    users_dao.insert_user(user)
    with notifications_admin.test_request_context():
        for _ in range(10):
            notifications_admin.test_client().post(
                url_for('main.sign_in'), data={
                    'email_address': 'valid@example.gov.uk',
                    'password': 'whatIsMyPassword!'})

        response = notifications_admin.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'valid@example.gov.uk',
                'password': 'val1dPassw0rd!'})

        assert response.status_code == 200
        assert 'Username or password is incorrect' in response.get_data(as_text=True)

        another_bad_attempt = notifications_admin.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'valid@example.gov.uk',
                'password': 'whatIsMyPassword!'})
        assert another_bad_attempt.status_code == 200
        assert 'Username or password is incorrect' in response.get_data(as_text=True)


def test_should_return_active_user_is_false_if_user_is_inactive(notifications_admin,
                                                                notifications_admin_db,
                                                                notify_db_session):
    user = User(email_address='inactive_user@example.gov.uk',
                password='val1dPassw0rd!',
                mobile_number='+441234123123',
                name='inactive user',
                created_at=datetime.now(),
                role_id=1,
                state='inactive')
    users_dao.insert_user(user)

    with notifications_admin.test_request_context():
        response = notifications_admin.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'inactive_user@example.gov.uk',
                'password': 'val1dPassw0rd!'})

    assert response.status_code == 200
    assert 'Username or password is incorrect' in response.get_data(as_text=True)


def test_should_return_200_when_user_does_not_exist(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        response = notifications_admin.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'does_not_exist@gov.uk',
                'password': 'doesNotExist!'})
    assert response.status_code == 200
    assert 'Username or password is incorrect' in response.get_data(as_text=True)


def test_should_return_200_when_user_is_not_active(notifications_admin, notifications_admin_db, notify_db_session):
    user = User(email_address='PendingUser@example.gov.uk',
                password='val1dPassw0rd!',
                mobile_number='+441234123123',
                name='pending user',
                created_at=datetime.now(),
                role_id=1,
                state='pending')
    users_dao.insert_user(user)
    with notifications_admin.test_request_context():
        response = notifications_admin.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'PendingUser@example.gov.uk',
                'password': 'val1dPassw0rd!'})
    assert response.status_code == 200
    assert 'Username or password is incorrect' in response.get_data(as_text=True)


def _set_up_mocker(mocker):
    mocker.patch("app.admin_api_client.send_sms")
    mocker.patch("app.admin_api_client.send_email")

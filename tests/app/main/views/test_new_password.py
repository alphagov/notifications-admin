from flask import url_for

from app.main.dao import users_dao
from app.main.encryption import check_hash
from app.notify_client.sender import generate_token
from tests.app.main import create_test_user


def test_should_render_new_password_template(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('request_password_reset')
            token = generate_token(user.email_address)
        response = client.get(url_for('.new_password', token=token))
        assert response.status_code == 200
        assert ' You can now create a new password for your account.' in response.get_data(as_text=True)


def test_should_render_new_password_template_with_message_of_bad_token(notifications_admin, notifications_admin_db,
                                                                       notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            create_test_user('request_password_reset')
            token = generate_token('no_user@d.gov.uk')
        response = client.get(url_for('.new_password', token=token))
        assert response.status_code == 200
        assert 'Message about email address does not exist. Some one needs to figure out the words here.' in \
               response.get_data(as_text=True)


def test_should_redirect_to_two_factor_when_password_reset_is_successful(notifications_admin,
                                                                         notifications_admin_db,
                                                                         notify_db_session,
                                                                         mocker):
    _set_up_mocker(mocker)
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('request_password_reset')
            token = generate_token(user.email_address)
        response = client.post(url_for('.new_password', token=token), data={'new_password': 'a-new_password'})
        assert response.status_code == 302
        assert response.location == url_for('.two_factor', _external=True)
        saved_user = users_dao.get_user_by_id(user.id)
        assert check_hash('a-new_password', saved_user.password)
        assert saved_user.state == 'active'


def test_should_redirect_to_forgot_password_with_flash_message_when_token_is_expired(notifications_admin,
                                                                                     notifications_admin_db,
                                                                                     notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            notifications_admin.config['TOKEN_MAX_AGE_SECONDS'] = -1000
            user = create_test_user('request_password_reset')
            token = generate_token(user.email_address)
        response = client.post(url_for('.new_password', token=token), data={'new_password': 'a-new_password'})
        assert response.status_code == 302
        assert response.location == url_for('.forgot_password', _external=True)
        notifications_admin.config['TOKEN_MAX_AGE_SECONDS'] = 3600


def test_should_redirect_to_forgot_password_when_user_is_active_should_be_request_password_reset(notifications_admin,
                                                                                                 notifications_admin_db,
                                                                                                 notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            token = generate_token(user.email_address)
        response = client.post(url_for('.new_password', token=token), data={'new_password': 'a-new_password'})
        assert response.status_code == 302
        assert response.location == url_for('.index', _external=True)


def _set_up_mocker(mocker):
    # mocker.patch("app.admin_api_client.send_sms")
    pass

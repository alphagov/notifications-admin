from flask import url_for

from app.main.dao import users_dao
from app.main.encryption import check_hash
from app.notify_client.sender import generate_token

import pytest


def test_should_render_new_password_template(app_,
                                             db_,
                                             db_session,
                                             mock_active_user,
                                             mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            mock_active_user.state = 'request_password_reset'
            token = generate_token(mock_active_user.email_address)
        response = client.get(url_for('.new_password', token=token))
        assert response.status_code == 200
        assert ' You can now create a new password for your account.' in response.get_data(as_text=True)


@pytest.mark.skipif(True, reason='Password reset no implemented')
def test_should_render_new_password_template_with_message_of_bad_token(app_,
                                                                       db_,
                                                                       db_session,
                                                                       mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            token = generate_token('no_user@d.gov.uk')
        response = client.get(url_for('.new_password', token=token))
        assert response.status_code == 200
        assert 'Message about email address does not exist. Some one needs to figure out the words here.' in \
               response.get_data(as_text=True)


@pytest.mark.skipif(True, reason='Password reset no implemented')
def test_should_redirect_to_two_factor_when_password_reset_is_successful(app_,
                                                                         db_,
                                                                         db_session,
                                                                         mock_send_sms,
                                                                         mock_active_user,
                                                                         mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            mock_active_user.state = 'request_password_reset'
            token = generate_token(mock_active_user.email_address)
        response = client.post(url_for('.new_password', token=token), data={'new_password': 'a-new_password'})
        assert response.status_code == 302
        assert response.location == url_for('.two_factor', _external=True)
        saved_user = users_dao.get_user_by_id(user.id)
        assert check_hash('a-new_password', saved_user.password)
        assert saved_user.state == 'active'


def test_should_redirect_to_forgot_password_with_flash_message_when_token_is_expired(app_,
                                                                                     db_,
                                                                                     db_session,
                                                                                     mock_active_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            app_.config['TOKEN_MAX_AGE_SECONDS'] = -1000
            mock_active_user.state = 'request_password_reset'
            token = generate_token(mock_active_user.email_address)
        response = client.post(url_for('.new_password', token=token), data={'new_password': 'a-new_password'})
        assert response.status_code == 302
        assert response.location == url_for('.forgot_password', _external=True)
        app_.config['TOKEN_MAX_AGE_SECONDS'] = 3600


@pytest.mark.skipif(True, reason='Password reset no implemented')
def test_should_redirect_to_forgot_pass_when_user_active_should_be_request_passw_reset(app_,
                                                                                       db_,
                                                                                       db_session,
                                                                                       mock_active_user,
                                                                                       mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            mock_active_user.state = 'request_password_reset'
            token = generate_token(mock_active_user.email_address)
        response = client.post(url_for('.new_password', token=token), data={'new_password': 'a-new_password'})
        assert response.status_code == 302
        assert response.location == url_for('.index', _external=True)

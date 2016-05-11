import json
from datetime import datetime

from flask import url_for
from notifications_utils.url_safe_token import generate_token


def test_should_render_new_password_template(app_,
                                             api_user_active,
                                             mock_login,
                                             mock_send_verify_code,
                                             mock_get_user_by_email_request_password_reset):
    with app_.test_request_context():
        with app_.test_client() as client:
            data = json.dumps({'email': api_user_active.email_address, 'created_at': str(datetime.utcnow())})
            token = generate_token(data, app_.config['SECRET_KEY'],
                                   app_.config['DANGEROUS_SALT'])
        response = client.get(url_for('.new_password', token=token))
        assert response.status_code == 200
        assert 'You can now create a new password for your account.' in response.get_data(as_text=True)


def test_should_return_404_when_email_address_does_not_exist(app_, mock_get_user_by_email_not_found):
    with app_.test_request_context():
        with app_.test_client() as client:
            data = json.dumps({'email': 'no_user@d.gov.uk', 'created_at': str(datetime.utcnow())})
            token = generate_token(data, app_.config['SECRET_KEY'], app_.config['DANGEROUS_SALT'])
        response = client.get(url_for('.new_password', token=token))
        assert response.status_code == 404


def test_should_redirect_to_two_factor_when_password_reset_is_successful(app_,
                                                                         mock_get_user_by_email_request_password_reset,
                                                                         mock_login,
                                                                         mock_send_verify_code):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = mock_get_user_by_email_request_password_reset.return_value
            data = json.dumps({'email': user.email_address, 'created_at': str(datetime.utcnow())})
            token = generate_token(data, app_.config['SECRET_KEY'], app_.config['DANGEROUS_SALT'])
        response = client.post(url_for('.new_password', token=token), data={'new_password': 'a-new_password'})
        assert response.status_code == 302
        assert response.location == url_for('.two_factor', _external=True)
        mock_get_user_by_email_request_password_reset.assert_called_once_with(user.email_address)


def test_should_redirect_index_if_user_has_already_changed_password(app_,
                                                                    mock_get_user_by_email_user_changed_password,
                                                                    mock_login,
                                                                    mock_send_verify_code):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = mock_get_user_by_email_user_changed_password.return_value
            data = json.dumps({'email': user.email_address, 'created_at': str(datetime.utcnow())})
            token = generate_token(data, app_.config['SECRET_KEY'], app_.config['DANGEROUS_SALT'])
        response = client.post(url_for('.new_password', token=token), data={'new_password': 'a-new_password'})
        assert response.status_code == 302
        assert response.location == url_for('.index', _external=True)
        mock_get_user_by_email_user_changed_password.assert_called_once_with(user.email_address)


def test_should_redirect_to_forgot_password_with_flash_message_when_token_is_expired(
        app_, mock_get_user_by_email_request_password_reset, mock_login
):
    with app_.test_request_context():
        with app_.test_client() as client:
            app_.config['TOKEN_MAX_AGE_SECONDS'] = -1000
            user = mock_get_user_by_email_request_password_reset.return_value
            token = generate_token(user.email_address, app_.config['SECRET_KEY'], app_.config['DANGEROUS_SALT'])
        response = client.post(url_for('.new_password', token=token), data={'new_password': 'a-new_password'})
        assert response.status_code == 302
        assert response.location == url_for('.forgot_password', _external=True)
        app_.config['TOKEN_MAX_AGE_SECONDS'] = 3600

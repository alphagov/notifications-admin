from flask import url_for, Response
from notifications_python_client.errors import HTTPError

import app


def test_should_render_forgot_password(app_):
    with app_.test_request_context():
        response = app_.test_client().get(url_for('.forgot_password'))
        assert response.status_code == 200
        assert 'We’ll send you an email to create a new password.' \
               in response.get_data(as_text=True)


def test_should_redirect_to_password_reset_sent_for_valid_email(
        app_,
        api_user_active,
        mocker):
    with app_.test_request_context():
        mocker.patch('app.user_api_client.send_reset_password_url', return_value=None)
        response = app_.test_client().post(
            url_for('.forgot_password'),
            data={'email_address': api_user_active.email_address})
        assert response.status_code == 200
        assert 'We’ve sent you an email with a link to reset your password.' \
               in response.get_data(as_text=True)
        app.user_api_client.send_reset_password_url.assert_called_once_with(api_user_active.email_address)


def test_should_redirect_to_password_reset_sent_for_missing_email(
        app_,
        api_user_active,
        mocker):
    with app_.test_request_context():

        mocker.patch('app.user_api_client.send_reset_password_url', side_effect=HTTPError(Response(status=404),
                                                                                          'Not found'))
        response = app_.test_client().post(
            url_for('.forgot_password'),
            data={'email_address': api_user_active.email_address})
        assert response.status_code == 200
        assert 'We’ve sent you an email with a link to reset your password.' \
               in response.get_data(as_text=True)
        app.user_api_client.send_reset_password_url.assert_called_once_with(api_user_active.email_address)

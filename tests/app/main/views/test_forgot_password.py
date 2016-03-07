from flask import url_for


def test_should_render_forgot_password(app_):
    with app_.test_request_context():
        response = app_.test_client().get(url_for('.forgot_password'))
        assert response.status_code == 200
        assert 'If you have forgotten your password, we can send you an email to create a new password.' \
               in response.get_data(as_text=True)


def test_should_redirect_to_password_reset_sent_for_valid_email(
        app_,
        api_user_active,
        mock_reset_user_password):
    with app_.test_request_context():
        response = app_.test_client().post(
            url_for('.forgot_password'),
            data={'email_address': api_user_active.email_address})
        assert response.status_code == 200
        assert (
            'You have been sent an email containing a link'
            ' to reset your password.') in response.get_data(as_text=True)
        mock_reset_user_password.assert_called_once_with(api_user_active.email_address)

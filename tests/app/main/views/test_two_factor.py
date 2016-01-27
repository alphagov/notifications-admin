from flask import json, url_for

from tests import create_test_user


def test_should_render_two_factor_page(app_,
                                       api_user_active,
                                       mock_user_dao_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            # TODO this lives here until we work out how to
            # reassign the session after it is lost mid register process
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address}
        response = client.get(url_for('main.two_factor'))
        assert response.status_code == 200
        assert '''We've sent you a text message with a verification code.''' in response.get_data(as_text=True)


def test_should_login_user_and_redirect_to_dashboard(app_,
                                                     api_user_active,
                                                     mock_get_user,
                                                     mock_user_dao_get_by_email,
                                                     mock_check_verify_code):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address}
            response = client.post(url_for('main.two_factor'),
                                   data={'sms_code': '12345'})

            assert response.status_code == 302
            assert response.location == url_for('main.choose_service', _external=True)


def test_should_return_200_with_sms_code_error_when_sms_code_is_wrong(app_,
                                                                      api_user_active,
                                                                      mock_user_dao_get_by_email,
                                                                      mock_check_verify_code_code_not_found):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address}
            response = client.post(url_for('main.two_factor'),
                                   data={'sms_code': '23456'})
            assert response.status_code == 200
            assert 'Code not found' in response.get_data(as_text=True)


def test_should_login_user_when_multiple_valid_codes_exist(app_,
                                                           api_user_active,
                                                           mock_get_user,
                                                           mock_user_dao_get_by_email,
                                                           mock_check_verify_code):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address}
            response = client.post(url_for('main.two_factor'),
                                   data={'sms_code': '23456'})
            assert response.status_code == 302

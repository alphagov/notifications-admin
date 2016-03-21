
from flask import url_for

from bs4 import BeautifulSoup


def test_should_render_email_verification_resent_show_email_address_and_resend_verify_email(app_,
                                                                                            mocker,
                                                                                            api_user_active,
                                                                                            mock_get_user_by_email,
                                                                                            mock_send_verify_email):

    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address}
            response = client.get(url_for('main.resend_email_verification'))
            assert response.status_code == 200

            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

            assert page.h1.string == 'Check your email'
            expected = "In order to verify your email address we've sent a new confirmation link to {}".format(api_user_active.email_address)  # noqa

            message = page.find_all('p')[1].text
            assert message == expected
            mock_send_verify_email.assert_called_with(api_user_active.id, api_user_active.email_address)


def test_should_render_text_code_not_received_template(app_,
                                                       api_user_active,
                                                       mock_get_user_by_email,
                                                       mock_send_verify_code):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address}
            response = client.get(url_for('main.check_and_resend_text_code'))
            assert response.status_code == 200
            assert 'Check your mobile phone number is correct and then resend the confirmation code.' \
                   in response.get_data(as_text=True)
            assert 'value="+441234123412"'


def test_should_check_and_redirect_to_verify(app_,
                                             api_user_active,
                                             mock_get_user_by_email,
                                             mock_update_user,
                                             mock_send_verify_code):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address}
            response = client.post(url_for('main.check_and_resend_text_code'),
                                   data={'mobile_number': '+447700900460'})
            assert response.status_code == 302
            assert response.location == url_for('main.verify', _external=True)


def test_should_update_mobile_number_resend_code(app_,
                                                 api_user_active,
                                                 mock_get_user_by_email,
                                                 mock_update_user,
                                                 mock_send_verify_code):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address}
            response = client.post(url_for('main.check_and_resend_text_code'),
                                   data={'mobile_number': '+447700900460'})
            assert response.status_code == 302
            assert response.location == url_for('main.verify', _external=True)
            api_user_active.mobile_number = '+447700900460'


def test_should_render_verification_code_not_received(app_,
                                                      api_user_active,
                                                      mock_send_verify_code):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address}
            response = client.get(url_for('main.verification_code_not_received'))
            assert response.status_code == 200
            assert 'Resend verification code' in response.get_data(as_text=True)
            assert 'If you no longer have access to the phone with the number you registered for this service, ' \
                   'speak to your service manager to reset the number.' in response.get_data(as_text=True)


def test_check_and_redirect_to_two_factor_if_user_active(app_,
                                                         api_user_active,
                                                         mock_get_user_by_email,
                                                         mock_send_verify_code):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address}
            response = client.get(url_for('main.check_and_resend_verification_code'))
            assert response.status_code == 302
            assert response.location == url_for('main.two_factor', _external=True)


def test_check_and_redirect_to_verify_if_user_pending(app_,
                                                      mocker,
                                                      api_user_pending,
                                                      mock_get_user_pending,
                                                      mock_send_verify_code):

    mocker.patch('app.user_api_client.get_user_by_email', return_value=api_user_pending)

    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_pending.id,
                    'email': api_user_pending.email_address}
            response = client.get(url_for('main.check_and_resend_verification_code'))
            assert response.status_code == 302
            assert response.location == url_for('main.verify', _external=True)


def test_should_create_new_code_for_user(app_,
                                         api_user_active,
                                         mock_get_user_by_email,
                                         mock_send_verify_code):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address}
            response = client.get(url_for('main.check_and_resend_verification_code'))
            assert response.status_code == 302
            assert response.location == url_for('main.two_factor', _external=True)

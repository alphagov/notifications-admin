
from flask import url_for

from bs4 import BeautifulSoup


def test_should_render_email_verification_resend_show_email_address_and_resend_verify_email(app_,
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


def test_should_render_correct_resend_template_for_active_user(app_,
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

            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
            assert page.h1.string == 'Resend verification code'
            # there shouldn't be a form for updating mobile number
            assert page.find('form') is None


def test_should_render_correct_resend_template_for_pending_user(app_,
                                                                mocker,
                                                                api_user_pending,
                                                                mock_send_verify_code):

    mocker.patch('app.user_api_client.get_user_by_email', return_value=api_user_pending)

    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_pending.id,
                    'email': api_user_pending.email_address}
            response = client.get(url_for('main.check_and_resend_text_code'))
            assert response.status_code == 200

            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
            assert page.h1.string == 'Check your mobile number'

            expected = 'Check your mobile phone number is correct and then resend the confirmation code.'
            message = page.find_all('p')[1].text
            assert message == expected
            assert page.find('form').input['value'] == api_user_pending.mobile_number


def test_should_resend_verify_code_and_update_mobile_for_pending_user(app_,
                                                                      mocker,
                                                                      api_user_pending,
                                                                      mock_update_user,
                                                                      mock_send_verify_code):

    mocker.patch('app.user_api_client.get_user_by_email', return_value=api_user_pending)

    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_pending.id,
                    'email': api_user_pending.email_address}
            response = client.post(url_for('main.check_and_resend_text_code'),
                                   data={'mobile_number': '+447700900460'})
            assert response.status_code == 302
            assert response.location == url_for('main.verify', _external=True)

            mock_update_user.assert_called_once_with(api_user_pending)
            mock_send_verify_code.assert_called_once_with(api_user_pending.id, 'sms', to='+447700900460')


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

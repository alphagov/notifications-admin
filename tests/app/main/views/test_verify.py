from flask import url_for

from bs4 import BeautifulSoup


def test_should_return_verify_template(app_,
                                       api_user_active,
                                       mock_send_verify_code):
    with app_.test_request_context():
        with app_.test_client() as client:
            # TODO this lives here until we work out how to
            # reassign the session after it is lost mid register process
            with client.session_transaction() as session:
                session['user_details'] = {'email_address': api_user_active.email_address, 'id': api_user_active.id}
            response = client.get(url_for('main.verify'))
            assert response.status_code == 200

            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
            assert page.h1.text == 'Text verification'
            assert page.p.text == "We've sent you a text message with a verification code."


def test_should_redirect_to_add_service_when_sms_code_is_correct(app_,
                                                                 api_user_active,
                                                                 mock_get_user,
                                                                 mock_update_user,
                                                                 mock_check_verify_code):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {'email_address': api_user_active.email_address, 'id': api_user_active.id}
            response = client.post(url_for('main.verify'),
                                   data={'sms_code': '12345'})
            assert response.status_code == 302
            assert response.location == url_for('main.add_service', first='first', _external=True)

            mock_check_verify_code.assert_called_once_with(api_user_active.id, '12345', 'sms')


def test_should_activate_user_after_verify(app_,
                                           api_user_active,
                                           mock_get_user,
                                           mock_send_verify_code,
                                           mock_check_verify_code,
                                           mock_update_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {'email_address': api_user_active.email_address, 'id': api_user_active.id}
            client.post(url_for('main.verify'),
                        data={'sms_code': '12345'})
            assert mock_update_user.called


def test_should_return_200_when_sms_code_is_wrong(app_,
                                                  api_user_active,
                                                  mock_get_user,
                                                  mock_check_verify_code_code_not_found):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {'email_address': api_user_active.email_address, 'id': api_user_active.id}
            response = client.post(url_for('main.verify'),
                                   data={'sms_code': '12345'})
            assert response.status_code == 200
            resp_data = response.get_data(as_text=True)
            assert resp_data.count('Code not found') == 1

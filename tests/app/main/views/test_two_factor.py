from flask import url_for
from tests.conftest import SERVICE_ONE_ID


def test_should_render_two_factor_page(app_,
                                       api_user_active,
                                       mock_get_user_by_email):
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
        assert '''We’ve sent you a text message with a verification code.''' in response.get_data(as_text=True)


def test_should_login_user_and_redirect_to_service_dashboard(app_,
                                                             api_user_active,
                                                             mock_get_user,
                                                             mock_get_user_by_email,
                                                             mock_check_verify_code,
                                                             mock_get_services_with_one_service):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address}
            response = client.post(url_for('main.two_factor'),
                                   data={'sms_code': '12345'})
            assert response.status_code == 302
            assert response.location == url_for(
                'main.service_dashboard',
                service_id=SERVICE_ONE_ID,
                _external=True
            )


def test_should_login_user_and_should_redirect_to_next_url(app_,
                                                           api_user_active,
                                                           mock_get_user,
                                                           mock_get_user_by_email,
                                                           mock_check_verify_code,
                                                           mock_get_services):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address}
            response = client.post(url_for('main.two_factor', next='/services/{}/dashboard'.format(SERVICE_ONE_ID)),
                                   data={'sms_code': '12345'})
            assert response.status_code == 302
            assert response.location == url_for(
                'main.service_dashboard',
                service_id=SERVICE_ONE_ID,
                _external=True
            )


def test_should_login_user_and_not_redirect_to_external_url(app_,
                                                            api_user_active,
                                                            mock_get_user,
                                                            mock_get_user_by_email,
                                                            mock_check_verify_code,
                                                            mock_get_services_with_one_service):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address}
            response = client.post(url_for('main.two_factor', next='http://www.google.com'),
                                   data={'sms_code': '12345'})
            assert response.status_code == 302
            assert response.location == url_for(
                'main.service_dashboard',
                service_id=SERVICE_ONE_ID,
                _external=True
            )


def test_should_login_user_and_redirect_to_choose_services(app_,
                                                           api_user_active,
                                                           mock_get_user,
                                                           mock_get_user_by_email,
                                                           mock_check_verify_code,
                                                           mock_get_services):
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
                                                                      mock_get_user_by_email,
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
                                                           mock_get_user_by_email,
                                                           mock_check_verify_code,
                                                           mock_get_services_with_one_service):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address}
            response = client.post(url_for('main.two_factor'),
                                   data={'sms_code': '23456'})
            assert response.status_code == 302


def test_remember_me_set(app_,
                         api_user_active,
                         mock_get_user,
                         mock_get_user_by_email,
                         mock_check_verify_code,
                         mock_get_services_with_one_service):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address}
            response = client.post(url_for('main.two_factor'),
                                   data={'sms_code': '23456', 'remember_me': True})
            assert response.status_code == 302


def test_two_factor_should_set_password_when_new_password_exists_in_session(app_,
                                                                            api_user_active,
                                                                            mock_get_user,
                                                                            mock_check_verify_code,
                                                                            mock_get_services_with_one_service,
                                                                            mock_update_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_details'] = {
                    'id': api_user_active.id,
                    'email': api_user_active.email_address,
                    'password': 'changedpassword'}

            response = client.post(url_for('main.two_factor'),
                                   data={'sms_code': '12345'})
            assert response.status_code == 302
            assert response.location == url_for(
                'main.service_dashboard',
                service_id=SERVICE_ONE_ID,
                _external=True
            )
            api_user_active.password = 'changedpassword'
            mock_update_user.assert_called_once_with(api_user_active)


def test_two_factor_reset_login_count_called(app_,
                                             api_user_locked,
                                             mock_get_locked_user,
                                             mock_update_user,
                                             mock_check_verify_code,
                                             mock_get_services_with_one_service):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                new_password = "1234567890"
                session['user_details'] = {
                    'id': api_user_locked.id,
                    'email': api_user_locked.email_address,
                    'password': new_password
                }
            response = client.post(url_for('main.two_factor'),
                                   data={'sms_code': '12345'})
            assert response.status_code == 302
            assert response.location == url_for(
                'main.service_dashboard',
                service_id=SERVICE_ONE_ID,
                _external=True
            )
            api_user_locked.reset_failed_login_count()
            api_user_locked.password = new_password
            mock_update_user.assert_called_with(api_user_locked)

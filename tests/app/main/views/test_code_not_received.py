from app.main.dao import verify_codes_dao
from flask import url_for


def test_should_render_email_code_not_received_template_and_populate_email_address(app_,
                                                                                   db_,
                                                                                   db_session,
                                                                                   mock_send_sms,
                                                                                   mock_send_email,
                                                                                   mock_active_user,
                                                                                   mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_email'] = mock_active_user.email_address
            response = client.get(url_for('main.check_and_resend_email_code'))
            assert response.status_code == 200
            assert 'Check your email address is correct and then resend the confirmation code' \
                   in response.get_data(as_text=True)
            assert 'value="test@user.gov.uk"' in response.get_data(as_text=True)


def test_should_check_and_resend_email_code_redirect_to_verify(app_,
                                                               db_,
                                                               db_session,
                                                               mock_send_sms,
                                                               mock_send_email,
                                                               mock_active_user,
                                                               mock_get_by_email,
                                                               mock_update_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_email'] = mock_active_user.email_address
                verify_codes_dao.add_code(mock_active_user.id, code='12345', code_type='email')
            response = client.post(url_for('main.check_and_resend_email_code'),
                                   data={'email_address': 'test@user.gov.uk'})
            assert response.status_code == 302
            assert response.location == url_for('main.verify', _external=True)


def test_should_render_text_code_not_received_template(app_,
                                                       db_,
                                                       db_session,
                                                       mock_send_sms,
                                                       mock_send_email,
                                                       mock_active_user,
                                                       mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_email'] = mock_active_user.email_address
                verify_codes_dao.add_code(mock_active_user.id, code='12345', code_type='sms')
            response = client.get(url_for('main.check_and_resend_text_code'))
            assert response.status_code == 200
            assert 'Check your mobile phone number is correct and then resend the confirmation code.' \
                   in response.get_data(as_text=True)
            assert 'value="+441234123412"'


def test_should_check_and_redirect_to_verify(app_,
                                             db_,
                                             db_session,
                                             mock_send_sms,
                                             mock_send_email,
                                             mock_active_user,
                                             mock_get_by_email,
                                             mock_update_mobile):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_email'] = mock_active_user.email_address
                verify_codes_dao.add_code(mock_active_user.id, code='12345', code_type='sms')
            response = client.post(url_for('main.check_and_resend_text_code'),
                                   data={'mobile_number': '+447700900460'})
            assert response.status_code == 302
            assert response.location == url_for('main.verify', _external=True)


def test_should_update_email_address_resend_code(app_,
                                                 db_,
                                                 db_session,
                                                 mock_send_sms,
                                                 mock_send_email,
                                                 mock_active_user,
                                                 mock_get_by_email,
                                                 mock_update_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_email'] = mock_active_user.email_address
                verify_codes_dao.add_code(user_id=mock_active_user.id, code='12345', code_type='email')
            response = client.post(url_for('main.check_and_resend_email_code'),
                                   data={'email_address': 'new@address.gov.uk'})
            assert response.status_code == 302
            assert response.location == url_for('main.verify', _external=True)
            assert mock_active_user.email_address == 'new@address.gov.uk'


def test_should_update_mobile_number_resend_code(app_,
                                                 db_,
                                                 db_session,
                                                 mock_send_sms,
                                                 mock_send_email,
                                                 mock_active_user,
                                                 mock_get_by_email,
                                                 mock_update_mobile):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_email'] = mock_active_user.email_address
                verify_codes_dao.add_code(user_id=mock_active_user.id, code='12345', code_type='sms')
            response = client.post(url_for('main.check_and_resend_text_code'),
                                   data={'mobile_number': '+447700900460'})
            assert response.status_code == 302
            assert response.location == url_for('main.verify', _external=True)
            assert mock_active_user.mobile_number == '+447700900460'


def test_should_render_verification_code_not_received(app_,
                                                      db_,
                                                      db_session,
                                                      mock_active_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_email'] = mock_active_user.email_address
            response = client.get(url_for('main.verification_code_not_received'))
            assert response.status_code == 200
            assert 'Resend verification code' in response.get_data(as_text=True)
            assert 'If you no longer have access to the phone with the number you registered for this service, ' \
                   'speak to your service manager to reset the number.' in response.get_data(as_text=True)


def test_check_and_redirect_to_two_factor(app_,
                                          db_,
                                          db_session,
                                          mock_active_user,
                                          mock_send_sms,
                                          mock_send_email,
                                          mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_email'] = mock_active_user.email_address
            response = client.get(url_for('main.check_and_resend_verification_code'))
            assert response.status_code == 302
            assert response.location == url_for('main.two_factor', _external=True)


def test_should_create_new_code_for_user(app_,
                                         db_,
                                         db_session,
                                         mock_active_user,
                                         mock_send_sms,
                                         mock_send_email,
                                         mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_email'] = mock_active_user.email_address
                verify_codes_dao.add_code(user_id=mock_active_user.id, code='12345', code_type='sms')
            response = client.get(url_for('main.check_and_resend_verification_code'))
            assert response.status_code == 302
            assert response.location == url_for('main.two_factor', _external=True)
            codes = verify_codes_dao.get_codes(user_id=mock_active_user.id, code_type='sms')
            assert len(codes) == 2
            for x in ([used.code_used for used in codes]):
                assert x is False

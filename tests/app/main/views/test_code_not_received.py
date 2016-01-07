from app.main.dao import verify_codes_dao, users_dao
from tests.app.main import create_test_user
from flask import url_for


def test_should_render_email_code_not_received_template_and_populate_email_address(notifications_admin,
                                                                                   notifications_admin_db,
                                                                                   notify_db_session,
                                                                                   mocker):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            with client.session_transaction() as session:
                _set_up_mocker(mocker)
                user = create_test_user('pending')
                session['user_email'] = user.email_address
            response = client.get(url_for('main.check_and_resend_email_code'))
            assert response.status_code == 200
            assert 'Check your email address is correct and then resend the confirmation code' \
                   in response.get_data(as_text=True)
            assert 'value="test@user.gov.uk"' in response.get_data(as_text=True)


def test_should_check_and_resend_email_code_redirect_to_verify(notifications_admin,
                                                               notifications_admin_db,
                                                               notify_db_session,
                                                               mocker):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            with client.session_transaction() as session:
                _set_up_mocker(mocker)
                user = create_test_user('pending')
                session['user_email'] = user.email_address
                verify_codes_dao.add_code(user.id, code='12345', code_type='email')
            response = client.post(url_for('main.check_and_resend_email_code'),
                                   data={'email_address': 'test@user.gov.uk'})
            assert response.status_code == 302
            assert response.location == url_for('main.verify', _external=True)


def test_should_render_text_code_not_received_template(notifications_admin,
                                                       notifications_admin_db,
                                                       notify_db_session,
                                                       mocker):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            with client.session_transaction() as session:
                _set_up_mocker(mocker)
                user = create_test_user('pending')
                session['user_email'] = user.email_address
                verify_codes_dao.add_code(user.id, code='12345', code_type='sms')
            response = client.get(url_for('main.check_and_resend_text_code'))
            assert response.status_code == 200
            assert 'Check your mobile phone number is correct and then resend the confirmation code.' \
                   in response.get_data(as_text=True)
            assert 'value="+441234123412"'


def test_should_check_and_redirect_to_verify(notifications_admin,
                                             notifications_admin_db,
                                             notify_db_session,
                                             mocker):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            with client.session_transaction() as session:
                _set_up_mocker(mocker)
                user = create_test_user('pending')
                session['user_email'] = user.email_address
                verify_codes_dao.add_code(user.id, code='12345', code_type='sms')
            response = client.post(url_for('main.check_and_resend_text_code'),
                                   data={'mobile_number': '+441234123412'})
            assert response.status_code == 302
            assert response.location == url_for('main.verify', _external=True)


def test_should_update_email_address_resend_code(notifications_admin,
                                                 notifications_admin_db,
                                                 notify_db_session,
                                                 mocker):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            with client.session_transaction() as session:
                _set_up_mocker(mocker)
                user = create_test_user('pending')
                session['user_email'] = user.email_address
                verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='email')
            response = client.post(url_for('main.check_and_resend_email_code'),
                                   data={'email_address': 'new@address.gov.uk'})
            assert response.status_code == 302
            assert response.location == url_for('main.verify', _external=True)
            updated_user = users_dao.get_user_by_id(user.id)
            assert updated_user.email_address == 'new@address.gov.uk'


def test_should_update_mobile_number_resend_code(notifications_admin,
                                                 notifications_admin_db,
                                                 notify_db_session,
                                                 mocker):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            with client.session_transaction() as session:
                _set_up_mocker(mocker)
                user = create_test_user('pending')
                session['user_email'] = user.email_address
                verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
            response = client.post(url_for('main.check_and_resend_text_code'),
                                   data={'mobile_number': '+443456789012'})
            assert response.status_code == 302
            assert response.location == url_for('main.verify', _external=True)
            updated_user = users_dao.get_user_by_id(user.id)
            assert updated_user.mobile_number == '+443456789012'


def test_should_render_verification_code_not_received(notifications_admin,
                                                      notifications_admin_db,
                                                      notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            with client.session_transaction() as session:
                user = create_test_user('active')
                session['user_email'] = user.email_address
            response = client.get(url_for('main.verification_code_not_received'))
            assert response.status_code == 200
            assert 'Resend verification code' in response.get_data(as_text=True)
            assert 'If you no longer have access to the phone with the number you registered for this service, ' \
                   'speak to your service manager to reset the number.' in response.get_data(as_text=True)


def test_check_and_redirect_to_two_factor(notifications_admin,
                                          notifications_admin_db,
                                          notify_db_session,
                                          mocker):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            with client.session_transaction() as session:
                user = create_test_user('active')
                session['user_email'] = user.email_address
                _set_up_mocker(mocker)
            response = client.get(url_for('main.check_and_resend_verification_code'))
            assert response.status_code == 302
            assert response.location == url_for('main.two_factor', _external=True)


def test_should_create_new_code_for_user(notifications_admin,
                                         notifications_admin_db,
                                         notify_db_session,
                                         mocker):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            with client.session_transaction() as session:
                user = create_test_user('active')
                session['user_email'] = user.email_address
                verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
                _set_up_mocker(mocker)
            response = client.get(url_for('main.check_and_resend_verification_code'))
            assert response.status_code == 302
            assert response.location == url_for('main.two_factor', _external=True)
            codes = verify_codes_dao.get_codes(user_id=user.id, code_type='sms')
            assert len(codes) == 2
            for x in ([used.code_used for used in codes]):
                assert x is False


def _set_up_mocker(mocker):
    mocker.patch("app.admin_api_client.send_sms")
    mocker.patch("app.admin_api_client.send_email")

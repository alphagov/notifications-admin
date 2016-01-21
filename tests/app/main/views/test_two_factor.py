from flask import json, url_for

from app.main.dao import verify_codes_dao
from tests import create_test_user


def test_should_render_two_factor_page(app_, db_, db_session, mock_api_user, mock_user_dao_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            # TODO this lives here until we work out how to
            # reassign the session after it is lost mid register process
            with client.session_transaction() as session:
                session['user_email'] = mock_api_user.email_address
        response = client.get(url_for('main.two_factor'))
        assert response.status_code == 200
        assert '''We've sent you a text message with a verification code.''' in response.get_data(as_text=True)


def test_should_login_user_and_redirect_to_dashboard(app_, db_, db_session, mock_api_user, mock_user_dao_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_email'] = mock_api_user.email_address
            verify_codes_dao.add_code(user_id=mock_api_user.id, code='12345', code_type='sms')
            response = client.post(url_for('main.two_factor'),
                                   data={'sms_code': '12345'})

            assert response.status_code == 302
            assert response.location == url_for('main.choose_service', _external=True)


def test_should_return_200_with_sms_code_error_when_sms_code_is_wrong(app_,
                                                                      db_,
                                                                      db_session,
                                                                      mock_api_user,
                                                                      mock_user_dao_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_email'] = mock_api_user.email_address
            verify_codes_dao.add_code(user_id=mock_api_user.id, code='12345', code_type='sms')
            response = client.post(url_for('main.two_factor'),
                                   data={'sms_code': '23456'})
            assert response.status_code == 200
            assert 'Code does not match' in response.get_data(as_text=True)


def test_should_login_user_when_multiple_valid_codes_exist(app_,
                                                           db_,
                                                           db_session,
                                                           mock_api_user,
                                                           mock_user_dao_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                session['user_email'] = mock_api_user.email_address
                verify_codes_dao.add_code(user_id=mock_api_user.id, code='23456', code_type='sms')
                verify_codes_dao.add_code(user_id=mock_api_user.id, code='12345', code_type='sms')
                verify_codes_dao.add_code(user_id=mock_api_user.id, code='34567', code_type='sms')
            assert len(verify_codes_dao.get_codes(user_id=mock_api_user.id, code_type='sms')) == 3
            response = client.post(url_for('main.two_factor'),
                                   data={'sms_code': '23456'})
            assert response.status_code == 302
            codes = verify_codes_dao.get_codes(user_id=mock_api_user.id, code_type='sms')
            # query will only return codes where code_used == False
            assert len(codes) == 0

from flask import json, url_for
from app.main.dao import users_dao, verify_codes_dao
from tests import create_test_user


def test_should_return_verify_template(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            # TODO this lives here until we work out how to
            # reassign the session after it is lost mid register process
            with client.session_transaction() as session:
                user = create_test_user('pending')
                session['user_email'] = user.email_address
            response = client.get(url_for('main.verify'))
            assert response.status_code == 200
            assert (
                "We've sent you confirmation codes by email and text message."
                " You need to enter both codes here.") in response.get_data(as_text=True)


def test_should_redirect_to_add_service_when_code_are_correct(app_,
                                                              db_,
                                                              db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                user = create_test_user('pending')
                session['user_email'] = user.email_address
            verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
            verify_codes_dao.add_code(user_id=user.id, code='23456', code_type='email')
            response = client.post(url_for('main.verify'),
                                   data={'sms_code': '12345',
                                         'email_code': '23456'})
            assert response.status_code == 302
            assert response.location == url_for('main.add_service', first='first', _external=True)


def test_should_activate_user_after_verify(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                user = create_test_user('pending')
                session['user_email'] = user.email_address
            verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
            verify_codes_dao.add_code(user_id=user.id, code='23456', code_type='email')
            client.post(url_for('main.verify'),
                        data={'sms_code': '12345',
                              'email_code': '23456'})

            after_verify = users_dao.get_user_by_id(user.id)
            assert after_verify.state == 'active'


def test_should_return_200_when_codes_are_wrong(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                user = create_test_user('pending')
                session['user_email'] = user.email_address
            verify_codes_dao.add_code(user_id=user.id, code='23345', code_type='sms')
            verify_codes_dao.add_code(user_id=user.id, code='98456', code_type='email')
            response = client.post(url_for('main.verify'),
                                   data={'sms_code': '12345',
                                         'email_code': '23456'})
            print(response.location)
            assert response.status_code == 200
            resp_data = response.get_data(as_text=True)
            assert resp_data.count('Code does not match') == 2


def test_should_mark_all_codes_as_used_when_many_codes_exist(app_,
                                                             db_,
                                                             db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            with client.session_transaction() as session:
                user = create_test_user('pending')
                session['user_email'] = user.email_address
            code1 = verify_codes_dao.add_code(user_id=user.id, code='23345', code_type='sms')
            code2 = verify_codes_dao.add_code(user_id=user.id, code='98456', code_type='email')
            code3 = verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
            code4 = verify_codes_dao.add_code(user_id=user.id, code='23412', code_type='email')
            response = client.post(url_for('main.verify'),
                                   data={'sms_code': '23345',
                                         'email_code': '23412'})
            assert response.status_code == 302
            assert verify_codes_dao.get_code_by_id(code1).code_used is True
            assert verify_codes_dao.get_code_by_id(code2).code_used is True
            assert verify_codes_dao.get_code_by_id(code3).code_used is True
            assert verify_codes_dao.get_code_by_id(code4).code_used is True

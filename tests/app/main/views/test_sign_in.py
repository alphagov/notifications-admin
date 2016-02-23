
from datetime import datetime

from app.main.dao import users_dao

from flask import url_for


def test_render_sign_in_returns_sign_in_template(app_):
    with app_.test_request_context():
        response = app_.test_client().get(url_for('main.sign_in'))
    assert response.status_code == 200
    assert 'Sign in' in response.get_data(as_text=True)
    assert 'Email address' in response.get_data(as_text=True)
    assert 'Password' in response.get_data(as_text=True)
    assert 'Forgotten password?' in response.get_data(as_text=True)


def test_logged_in_user_redirects_to_choose_service(app_,
                                                    api_user_active,
                                                    mock_get_user_by_email,
                                                    mock_login):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.sign_in'))
            assert response.status_code == 302

            response = client.get(url_for('main.sign_in', follow_redirects=True))
            assert response.location == url_for('main.choose_service', _external=True)


def test_process_sign_in_return_2fa_template(app_,
                                             api_user_active,
                                             mock_send_verify_code,
                                             mock_get_user,
                                             mock_get_user_by_email,
                                             mock_verify_password):

    with app_.test_request_context():
        response = app_.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'valid@example.gov.uk',
                'password': 'val1dPassw0rd!'})
        assert response.status_code == 302
        assert response.location == url_for('.two_factor', _external=True)
    mock_verify_password.assert_called_with(api_user_active.id, 'val1dPassw0rd!')


def test_should_return_locked_out_true_when_user_is_locked(app_,
                                                           mock_get_user_by_email_locked):
    with app_.test_request_context():
        resp = app_.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'valid@example.gov.uk',
                'password': 'whatIsMyPassword!'})
        assert resp.status_code == 200
        assert 'Username or password is incorrect' in resp.get_data(as_text=True)


def test_should_return_active_user_is_false_if_user_is_inactive(app_, mock_get_user_by_email_inactive):

    with app_.test_request_context():
        response = app_.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'inactive_user@example.gov.uk',
                'password': 'val1dPassw0rd!'})

    assert response.status_code == 200
    assert 'Username or password is incorrect' in response.get_data(as_text=True)


def test_should_return_200_when_user_does_not_exist(app_, mock_get_user_by_email_not_found):
    with app_.test_request_context():
        response = app_.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'notfound@gov.uk',
                'password': 'doesNotExist!'})
    assert response.status_code == 200
    assert 'Username or password is incorrect' in response.get_data(as_text=True)


def test_should_return_redirect_when_user_is_pending(app_,
                                                     mock_get_user_by_email_pending,
                                                     mock_verify_password):
    with app_.test_request_context():
        response = app_.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'pending_user@example.gov.uk',
                'password': 'val1dPassw0rd!'})
        assert response.status_code == 302
        assert response.location == url_for('main.verify', _external=True)


def test_not_fresh_session_login(app_,
                                 api_user_active,
                                 mock_login,
                                 mock_get_user_by_email,
                                 mock_verify_password,
                                 mock_get_services_with_one_service):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            with client.session_transaction() as session:
                assert session['_fresh']
                session['_fresh'] = False
            # This should skip the two factor
            response = client.post(
                url_for('main.sign_in'), data={
                    'email_address': api_user_active.email_address,
                    'password': 'val1dPassw0rd!'})
        assert response.status_code == 302
        service_dct = mock_get_services_with_one_service(api_user_active.id)['data'][0]
        assert response.location == url_for(
            'main.service_dashboard', service_id=service_dct['id'], _external=True)

import uuid

import pytest
from bs4 import BeautifulSoup
from flask import url_for


def test_render_sign_in_template_for_new_user(
    client
):
    response = client.get(url_for('main.sign_in', next=None))
    assert response.status_code == 200
    resp = response.get_data(as_text=True)
    assert 'Sign in' in resp
    assert 'Email address' in resp
    assert 'Password' in resp
    assert 'Forgot your password?' in resp
    assert 'If you do not have an account, you can' in resp
    assert 'Sign in again' not in resp


def test_sign_in_explains_session_timeout(client):
    response = client.get(url_for('main.sign_in', next='/foo'))
    assert response.status_code == 200
    assert 'We signed you out because you haven’t used Notify for a while.' in response.get_data(as_text=True)


def test_sign_in_explains_other_browser(logged_in_client, api_user_active, mocker):
    api_user_active.current_session_id = str(uuid.UUID(int=1))
    mocker.patch('app.user_api_client.get_user', return_value=api_user_active)

    with logged_in_client.session_transaction() as session:
        session['current_session_id'] = str(uuid.UUID(int=2))

    response = logged_in_client.get(url_for('main.sign_in', next='/foo'))

    assert response.status_code == 200
    assert 'We signed you out because you logged in to Notify on another device' in response.get_data(as_text=True)


def test_doesnt_redirect_to_sign_in_if_no_session_info(
    logged_in_client, api_user_active
):
    assert api_user_active.current_session_id is None

    with logged_in_client.session_transaction() as session:
        session['current_session_id'] = None

    response = logged_in_client.get(url_for('main.add_service'))
    assert response.status_code == 200


@pytest.mark.parametrize('db_sess_id, cookie_sess_id', [
    pytest.param(None, None, marks=pytest.mark.xfail),  # OK - not used notify since browser signout was implemented

    (uuid.UUID(int=1), None),  # BAD - has used other browsers before but this is a brand new browser with no cookie
    (uuid.UUID(int=1), uuid.UUID(int=2)),  # BAD - this person has just signed in on a different browser
])
def test_redirect_to_sign_in_if_logged_in_from_other_browser(
    logged_in_client,
    api_user_active,
    mocker,
    db_sess_id,
    cookie_sess_id
):
    api_user_active.current_session_id = db_sess_id
    mocker.patch('app.user_api_client.get_user', return_value=api_user_active)
    with logged_in_client.session_transaction() as session:
        session['current_session_id'] = str(cookie_sess_id)

    response = logged_in_client.get(url_for('main.choose_account'))
    assert response.status_code == 302
    assert response.location == url_for('main.sign_in', next='/accounts', _external=True)


def test_logged_in_user_redirects_to_account(
    client_request
):
    client_request.get(
        'main.sign_in',
        _expected_status=302,
        _expected_redirect=url_for('main.show_accounts_or_dashboard', _external=True),
    )


@pytest.mark.parametrize('email_address, password', [
    ('valid@example.gov.uk', 'val1dPassw0rd!'),
    (' valid@example.gov.uk  ', '  val1dPassw0rd!  '),
])
def test_process_sms_auth_sign_in_return_2fa_template(
    client,
    api_user_active,
    mock_send_verify_code,
    mock_get_user,
    mock_get_user_by_email,
    mock_verify_password,
    email_address,
    password,
):
    response = client.post(
        url_for('main.sign_in'), data={
            'email_address': email_address,
            'password': password})
    assert response.status_code == 302
    assert response.location == url_for('.two_factor', _external=True)
    mock_verify_password.assert_called_with(api_user_active.id, password)
    mock_get_user_by_email.assert_called_with('valid@example.gov.uk')


def test_process_email_auth_sign_in_return_2fa_template(
    client,
    api_user_active_email_auth,
    mock_send_verify_code,
    mock_verify_password,
    mocker
):
    mocker.patch('app.user_api_client.get_user', return_value=api_user_active_email_auth)
    mocker.patch('app.user_api_client.get_user_by_email', return_value=api_user_active_email_auth)

    response = client.post(
        url_for('main.sign_in'), data={
            'email_address': 'valid@example.gov.uk',
            'password': 'val1dPassw0rd!'})
    assert response.status_code == 302
    assert response.location == url_for('.two_factor_email_sent', _external=True)
    mock_send_verify_code.assert_called_with(api_user_active_email_auth.id, 'email', None)
    mock_verify_password.assert_called_with(api_user_active_email_auth.id, 'val1dPassw0rd!')


def test_should_return_locked_out_true_when_user_is_locked(
    client,
    mock_get_user_by_email_locked,
):
    resp = client.post(
        url_for('main.sign_in'), data={
            'email_address': 'valid@example.gov.uk',
            'password': 'whatIsMyPassword!'})
    assert resp.status_code == 200
    assert 'The email address or password you entered is incorrect' in resp.get_data(as_text=True)


def test_should_return_200_when_user_does_not_exist(
    client,
    mock_get_user_by_email_not_found,
):
    response = client.post(
        url_for('main.sign_in'), data={
            'email_address': 'notfound@gov.uk',
            'password': 'doesNotExist!'})
    assert response.status_code == 200
    assert 'The email address or password you entered is incorrect' in response.get_data(as_text=True)


def test_should_return_redirect_when_user_is_pending(
    client,
    mock_get_user_by_email_pending,
    mock_verify_password,
):
    response = client.post(
        url_for('main.sign_in'), data={
            'email_address': 'pending_user@example.gov.uk',
            'password': 'val1dPassw0rd!'}, follow_redirects=True)

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string == 'Sign in'
    assert response.status_code == 200


def test_should_attempt_redirect_when_user_is_pending(
    client,
    mock_get_user_by_email_pending,
    mock_verify_password,
):
    response = client.post(
        url_for('main.sign_in'), data={
            'email_address': 'pending_user@example.gov.uk',
            'password': 'val1dPassw0rd!'})
    assert response.location == url_for('main.resend_email_verification', _external=True)
    assert response.status_code == 302


def test_email_address_is_treated_case_insensitively_when_signing_in_as_invited_user(
    client,
    mocker,
    mock_verify_password,
    api_user_active,
    sample_invite,
    mock_accept_invite,
    mock_send_verify_code
):
    sample_invite['email_address'] = 'TEST@user.gov.uk'

    mocker.patch('app.user_api_client.get_user_by_email_or_none', return_value=api_user_active)
    mocker.patch('app.main.views.sign_in._get_and_verify_user', return_value=api_user_active)

    with client.session_transaction() as session:
        session['invited_user'] = sample_invite

    response = client.post(
        url_for('main.sign_in'), data={
            'email_address': 'test@user.gov.uk',
            'password': 'val1dPassw0rd!'})

    assert mock_accept_invite.called
    assert response.status_code == 302
    assert mock_send_verify_code.called

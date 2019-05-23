from bs4 import BeautifulSoup
from flask import url_for

from tests.conftest import (
    SERVICE_ONE_ID,
    normalize_spaces,
    set_config,
    url_for_endpoint_with_token,
)


def test_should_render_two_factor_page(
    client,
    api_user_active,
    mock_get_user_by_email,
):
    # TODO this lives here until we work out how to
    # reassign the session after it is lost mid register process
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address']}
    response = client.get(url_for('main.two_factor'))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.select_one('main p').text.strip() == (
        'We’ve sent you a text message with a security code.'
    )
    assert page.select_one('label').text.strip(
        'Text message code'
    )
    assert page.select_one('input')['type'] == 'tel'
    assert page.select_one('input')['pattern'] == '[0-9]*'


def test_should_login_user_and_should_redirect_to_next_url(
    client,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_check_verify_code,
    mock_create_event,
):
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address']}
    response = client.post(url_for('main.two_factor', next='/services/{}'.format(SERVICE_ONE_ID)),
                           data={'sms_code': '12345'})
    assert response.status_code == 302
    assert response.location == url_for(
        'main.service_dashboard',
        service_id=SERVICE_ONE_ID,
        _external=True
    )


def test_should_login_user_and_not_redirect_to_external_url(
    client,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_check_verify_code,
    mock_get_services_with_one_service,
    mock_create_event,
):
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address']}
    response = client.post(url_for('main.two_factor', next='http://www.google.com'),
                           data={'sms_code': '12345'})
    assert response.status_code == 302
    assert response.location == url_for('main.show_accounts_or_dashboard', _external=True)


def test_should_login_user_and_redirect_to_show_accounts(
    client,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_check_verify_code,
    mock_create_event,
):
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address']}
    response = client.post(url_for('main.two_factor'),
                           data={'sms_code': '12345'})

    assert response.status_code == 302
    assert response.location == url_for('main.show_accounts_or_dashboard', _external=True)


def test_should_return_200_with_sms_code_error_when_sms_code_is_wrong(
    client,
    api_user_active,
    mock_get_user_by_email,
    mock_check_verify_code_code_not_found,
):
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address']}
    response = client.post(url_for('main.two_factor'),
                           data={'sms_code': '23456'})
    assert response.status_code == 200
    assert 'Code not found' in response.get_data(as_text=True)


def test_should_login_user_when_multiple_valid_codes_exist(
    client,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_check_verify_code,
    mock_get_services_with_one_service,
    mock_create_event,
):
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address']}
    response = client.post(url_for('main.two_factor'),
                           data={'sms_code': '23456'})
    assert response.status_code == 302


def test_two_factor_should_set_password_when_new_password_exists_in_session(
    client,
    api_user_active,
    mock_get_user,
    mock_check_verify_code,
    mock_get_services_with_one_service,
    mock_update_user_password,
    mock_create_event,
):
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address'],
            'password': 'changedpassword'}

    response = client.post(url_for('main.two_factor'),
                           data={'sms_code': '12345'})
    assert response.status_code == 302
    assert response.location == url_for('main.show_accounts_or_dashboard', _external=True)

    mock_update_user_password.assert_called_once_with(api_user_active['id'], 'changedpassword')


def test_two_factor_returns_error_when_user_is_locked(
    client,
    api_user_locked,
    mock_get_locked_user,
    mock_check_verify_code_code_not_found,
    mock_get_services_with_one_service
):
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_locked['id'],
            'email': api_user_locked['email_address'],
        }
    response = client.post(url_for('main.two_factor'),
                           data={'sms_code': '12345'})
    assert response.status_code == 200
    assert 'Code not found' in response.get_data(as_text=True)


def test_two_factor_should_redirect_to_sign_in_if_user_not_in_session(
    client,
    api_user_active,
    mock_get_user,
):
    response = client.post(url_for('main.two_factor'),
                           data={'sms_code': '12345'})
    assert response.status_code == 302
    assert response.location == url_for('main.sign_in', _external=True)


def test_two_factor_should_activate_pending_user(
    client,
    mocker,
    api_user_pending,
    mock_check_verify_code,
    mock_create_event,
    mock_activate_user,
):
    mocker.patch('app.user_api_client.get_user', return_value=api_user_pending)
    mocker.patch('app.service_api_client.get_services', return_value={'data': []})
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_pending['id'],
            'email_address': api_user_pending['email_address']
        }
    client.post(url_for('main.two_factor'), data={'sms_code': '12345'})

    assert mock_activate_user.called


def test_valid_two_factor_email_link_logs_in_user(
    client,
    valid_token,
    mock_get_user,
    mock_get_services_with_one_service,
    mocker,
    mock_create_event,
):
    mocker.patch('app.user_api_client.check_verify_code', return_value=(True, ''))

    response = client.get(
        url_for_endpoint_with_token('main.two_factor_email', token=valid_token),
    )

    assert response.status_code == 302
    assert response.location == url_for('main.show_accounts_or_dashboard', _external=True)


def test_two_factor_email_link_has_expired(
    app_,
    valid_token,
    client,
    mock_send_verify_code,
    fake_uuid
):

    with set_config(app_, 'EMAIL_2FA_EXPIRY_SECONDS', -1):
        response = client.get(
            url_for_endpoint_with_token('main.two_factor_email', token=valid_token),
            follow_redirects=True,
        )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.h1.text.strip() == 'The link has expired'
    mock_send_verify_code.assert_not_called


def test_two_factor_email_link_is_invalid(
    client
):
    token = 12345
    response = client.get(
        url_for('main.two_factor_email', token=token),
        follow_redirects=True
    )
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert normalize_spaces(
        page.select_one('.banner-dangerous').text
    ) == "There’s something wrong with the link you’ve used."
    assert response.status_code == 404


def test_two_factor_email_link_is_already_used(
    client,
    valid_token,
    mocker,
    mock_send_verify_code

):
    mocker.patch('app.user_api_client.check_verify_code', return_value=(False, 'Code has expired'))

    response = client.get(
        url_for_endpoint_with_token('main.two_factor_email', token=valid_token),
        follow_redirects=True
    )

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert response.status_code == 200

    assert page.h1.text.strip() == 'The link has expired'
    mock_send_verify_code.assert_not_called


def test_two_factor_email_link_when_user_is_locked_out(
    client,
    valid_token,
    mocker,
    mock_send_verify_code
):
    mocker.patch('app.user_api_client.check_verify_code', return_value=(False, 'Code not found'))

    response = client.get(
        url_for_endpoint_with_token('main.two_factor_email', token=valid_token),
        follow_redirects=True
    )

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert response.status_code == 200

    assert page.h1.text.strip() == 'The link has expired'
    mock_send_verify_code.assert_not_called


def test_two_factor_email_link_used_when_user_already_logged_in(
    logged_in_client,
    valid_token
):
    response = logged_in_client.get(
        url_for_endpoint_with_token('main.two_factor_email', token=valid_token)
    )
    assert response.status_code == 302
    assert response.location == url_for('main.show_accounts_or_dashboard', _external=True)

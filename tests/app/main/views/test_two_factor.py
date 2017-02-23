from flask import url_for
from tests.conftest import SERVICE_ONE_ID

from unittest.mock import ANY


def test_should_render_two_factor_page(
    client,
    api_user_active,
    mock_get_user_by_email,
):
    # TODO this lives here until we work out how to
    # reassign the session after it is lost mid register process
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active.id,
            'email': api_user_active.email_address}
    response = client.get(url_for('main.two_factor'))
    assert response.status_code == 200
    assert '''We’ve sent you a text message with a security code.''' in response.get_data(as_text=True)


def test_should_login_user_and_redirect_to_service_dashboard(
    client,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_check_verify_code,
    mock_get_services_with_one_service,
    mock_events,
):
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

    mock_events.assert_called_with('sucessful_login', ANY)


def test_should_login_user_and_should_redirect_to_next_url(
    client,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_check_verify_code,
    mock_get_services,
):
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


def test_should_login_user_and_not_redirect_to_external_url(
    client,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_check_verify_code,
    mock_get_services_with_one_service,
):
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


def test_should_login_user_and_redirect_to_choose_services(
    client,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_check_verify_code,
    mock_get_services,
):
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active.id,
            'email': api_user_active.email_address}
    response = client.post(url_for('main.two_factor'),
                           data={'sms_code': '12345'})

    assert response.status_code == 302
    assert response.location == url_for('main.choose_service', _external=True)


def test_should_return_200_with_sms_code_error_when_sms_code_is_wrong(
    client,
    api_user_active,
    mock_get_user_by_email,
    mock_check_verify_code_code_not_found,
):
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active.id,
            'email': api_user_active.email_address}
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
):
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active.id,
            'email': api_user_active.email_address}
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
):
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
    mock_update_user_password.assert_called_once_with(api_user_active.id, password='changedpassword')


def test_two_factor_returns_error_when_user_is_locked(
    client,
    api_user_locked,
    mock_get_locked_user,
    mock_check_verify_code,
    mock_get_services_with_one_service
):
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_locked.id,
            'email': api_user_locked.email_address,
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
    mock_update_user,
):
    mocker.patch('app.user_api_client.get_user', return_value=api_user_pending)
    mocker.patch('app.service_api_client.get_services', return_value={'data': []})
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_pending.id,
            'email_address': api_user_pending.email_address
        }
    client.post(url_for('main.two_factor'), data={'sms_code': '12345'})

    assert mock_update_user.called
    assert api_user_pending.is_active

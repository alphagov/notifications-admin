import pytest
from bs4 import BeautifulSoup
from flask import url_for


def test_should_render_email_verification_resend_show_email_address_and_resend_verify_email(
    client,
    mocker,
    api_user_active,
    mock_get_user_by_email,
    mock_send_verify_email,
):
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address']}
    response = client.get(url_for('main.resend_email_verification'))
    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.h1.string == 'Check your email'
    expected = "A new confirmation email has been sent to {}".format(api_user_active['email_address'])

    message = page.find_all('p')[1].text
    assert message == expected
    mock_send_verify_email.assert_called_with(api_user_active['id'], api_user_active['email_address'])


def test_should_render_correct_resend_template_for_active_user(
    client,
    api_user_active,
    mock_get_user_by_email,
    mock_send_verify_code,
):
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address']}
    response = client.get(url_for('main.check_and_resend_text_code'))
    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string == 'Resend security code'
    # there shouldn't be a form for updating mobile number
    assert page.find('form') is None


def test_should_render_correct_resend_template_for_pending_user(
    client,
    mocker,
    api_user_pending,
    mock_send_verify_code,
):

    mocker.patch('app.user_api_client.get_user_by_email', return_value=api_user_pending)

    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_pending['id'],
            'email': api_user_pending['email_address']}
    response = client.get(url_for('main.check_and_resend_text_code'))
    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string == 'Check your mobile number'

    expected = 'Check your mobile phone number is correct and then resend the security code.'
    message = page.find_all('p')[1].text
    assert message == expected
    assert page.find('form').input['value'] == api_user_pending['mobile_number']


@pytest.mark.parametrize('phone_number_to_register_with', [
    '+447700900460',
    '+1800-555-555',
])
def test_should_resend_verify_code_and_update_mobile_for_pending_user(
    client,
    mocker,
    api_user_pending,
    mock_update_user_attribute,
    mock_send_verify_code,
    phone_number_to_register_with,
):
    mocker.patch('app.user_api_client.get_user_by_email', return_value=api_user_pending)

    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_pending['id'],
            'email': api_user_pending['email_address']}
    response = client.post(url_for('main.check_and_resend_text_code'),
                           data={'mobile_number': phone_number_to_register_with})
    assert response.status_code == 302
    assert response.location == url_for('main.verify', _external=True)

    mock_update_user_attribute.assert_called_once_with(
        api_user_pending['id'],
        mobile_number=phone_number_to_register_with,
    )
    mock_send_verify_code.assert_called_once_with(
        api_user_pending['id'],
        'sms',
        phone_number_to_register_with,
    )


def test_check_and_redirect_to_two_factor_if_user_active(
    client,
    api_user_active,
    mock_get_user_by_email,
    mock_send_verify_code,
):
    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address']}
    response = client.get(url_for('main.check_and_resend_verification_code'))
    assert response.status_code == 302
    assert response.location == url_for('main.two_factor', _external=True)


def test_check_and_redirect_to_verify_if_user_pending(
    client,
    mocker,
    api_user_pending,
    mock_get_user_pending,
    mock_send_verify_code,
):

    mocker.patch('app.user_api_client.get_user_by_email', return_value=api_user_pending)

    with client.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_pending['id'],
            'email': api_user_pending['email_address']}
    response = client.get(url_for('main.check_and_resend_verification_code'))
    assert response.status_code == 302
    assert response.location == url_for('main.verify', _external=True)


@pytest.mark.parametrize('endpoint', [
    'main.resend_email_verification',
    'main.check_and_resend_text_code',
    'main.check_and_resend_verification_code',
])
def test_redirect_to_sign_in_if_not_logged_in(
    client,
    endpoint,
):
    response = client.get(url_for(endpoint))

    assert response.location == url_for('main.sign_in', _external=True)
    assert response.status_code == 302

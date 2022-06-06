import json
import uuid
from unittest.mock import Mock

from flask import session as flask_session
from flask import url_for
from itsdangerous import SignatureExpired
from notifications_python_client.errors import HTTPError

from app.main.views.verify import activate_user
from tests.conftest import create_user


def test_should_return_verify_template(
    client_request,
    api_user_active,
    mock_send_verify_code,
):
    client_request.logout()
    # TODO this lives here until we work out how to
    # reassign the session after it is lost mid register process
    with client_request.session_transaction() as session:
        session['user_details'] = {'email_address': api_user_active['email_address'], 'id': api_user_active['id']}
    page = client_request.get('main.verify')

    assert page.h1.text == 'Check your phone'
    message = page.select('main p')[0].text
    assert message == "We’ve sent you a text message with a security code."


def test_should_redirect_to_add_service_when_sms_code_is_correct(
    client_request,
    api_user_active,
    mocker,
    mock_update_user_attribute,
    mock_check_verify_code,
    mock_create_event,
    fake_uuid,
):
    api_user_active['current_session_id'] = str(uuid.UUID(int=1))
    mocker.patch('app.user_api_client.get_user', return_value=api_user_active)

    with client_request.session_transaction() as session:
        session['user_details'] = {'email_address': api_user_active['email_address'], 'id': api_user_active['id']}
        # user's only just created their account so no session in the cookie
        session.pop('current_session_id', None)

    client_request.post(
        'main.verify',
        _data={'sms_code': '12345'},
        _expected_redirect=url_for('main.add_service', first='first'),
    )

    # make sure the current_session_id has changed to what the API returned
    with client_request.session_transaction() as session:
        assert session['current_session_id'] == str(uuid.UUID(int=1))

    mock_check_verify_code.assert_called_once_with(api_user_active['id'], '12345', 'sms')


def test_should_activate_user_after_verify(
    client_request,
    mocker,
    api_user_pending,
    mock_send_verify_code,
    mock_check_verify_code,
    mock_create_event,
    mock_activate_user,
):
    client_request.logout()
    mocker.patch('app.user_api_client.get_user', return_value=api_user_pending)
    with client_request.session_transaction() as session:
        session['user_details'] = {
            'email_address': api_user_pending['email_address'],
            'id': api_user_pending['id']
        }
    client_request.post('main.verify', _data={'sms_code': '12345'})
    assert mock_activate_user.called


def test_should_return_200_when_sms_code_is_wrong(
    client_request,
    api_user_active,
    mock_check_verify_code_code_not_found,
):
    with client_request.session_transaction() as session:
        session['user_details'] = {
            'email_address': api_user_active['email_address'],
            'id': api_user_active['id'],
        }

    page = client_request.post(
        'main.verify',
        _data={'sms_code': '12345'},
        _expected_status=200,
    )

    assert len(page.select('.govuk-error-message')) == 1
    assert 'Code not found' in page.select_one('.govuk-error-message').text


def test_verify_email_redirects_to_verify_if_token_valid(
    client_request,
    mocker,
    api_user_pending,
    mock_get_user_pending,
    mock_send_verify_code,
    mock_check_verify_code,
):
    token_data = {"user_id": api_user_pending['id'], "secret_code": 'UNUSED'}
    mocker.patch('app.main.views.verify.check_token', return_value=json.dumps(token_data))

    client_request.get(
        'main.verify_email',
        token='notreal',
        _expected_redirect=url_for('main.verify'),
    )

    assert not mock_check_verify_code.called
    mock_send_verify_code.assert_called_once_with(api_user_pending['id'], 'sms', api_user_pending['mobile_number'])

    with client_request.session_transaction() as session:
        assert session['user_details'] == {'email': api_user_pending['email_address'], 'id': api_user_pending['id']}


def test_verify_email_doesnt_verify_sms_if_user_on_email_auth(
    client_request,
    mocker,
    mock_send_verify_code,
    mock_check_verify_code,
    mock_activate_user,
    fake_uuid,
):
    pending_user_with_email_auth = create_user(auth_type='email_auth', state='pending', id=fake_uuid)

    mocker.patch('app.user_api_client.get_user', return_value=pending_user_with_email_auth)
    token_data = {"user_id": pending_user_with_email_auth['id'], "secret_code": 'UNUSED'}
    mocker.patch('app.main.views.verify.check_token', return_value=json.dumps(token_data))

    client_request.get(
        'main.verify_email',
        token='notreal',
        _expected_redirect=url_for('main.add_service', first='first'),
    )

    assert not mock_check_verify_code.called
    assert not mock_send_verify_code.called

    mock_activate_user.assert_called_once_with(pending_user_with_email_auth['id'])

    # user is logged in
    with client_request.session_transaction() as session:
        assert session['user_id'] == pending_user_with_email_auth['id']


def test_verify_email_redirects_to_email_sent_if_token_expired(
    client_request,
    mocker,
    api_user_pending,
):
    client_request.logout()
    mocker.patch('app.main.views.verify.check_token', side_effect=SignatureExpired('expired'))

    client_request.get(
        'main.verify_email',
        token='notreal',
        _expected_redirect=url_for('main.resend_email_verification'),
    )


def test_verify_email_redirects_to_sign_in_if_user_active(
    client_request,
    mocker,
    api_user_active,
    mock_get_user,
    mock_send_verify_code,
    mock_check_verify_code,
):
    client_request.logout()
    token_data = {"user_id": api_user_active['id'], "secret_code": 12345}
    mocker.patch('app.main.views.verify.check_token', return_value=json.dumps(token_data))

    page = client_request.get('main.verify_email', token='notreal', _follow_redirects=True)

    assert page.h1.text == 'Sign in'
    flash_banner = page.find('div', class_='banner-dangerous').string.strip()
    assert flash_banner == "That verification link has expired."


def test_verify_redirects_to_sign_in_if_not_logged_in(
    client_request
):
    client_request.logout()
    client_request.get(
        'main.verify',
        _expected_redirect=url_for('main.sign_in'),
    )


def test_activate_user_redirects_to_service_dashboard_if_user_already_belongs_to_service(
    mocker,
    client_request,
    service_one,
    sample_invite,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_invited_user_by_id,
):
    mocker.patch('app.user_api_client.add_user_to_service', side_effect=HTTPError(
        response=Mock(
            status_code=400,
            json={
                "result": "error",
                "message": {f"User id: {api_user_active['id']} already part of service id: {service_one['id']}"}
            },
        ),
        message=f"User id: {api_user_active['id']} already part of service id: {service_one['id']}"
    ))

    # Can't use `with client.session_transaction()...` here since activate_session is not a view function
    flask_session['invited_user_id'] = sample_invite['id']

    response = activate_user(api_user_active['id'])

    assert response.location == url_for('main.service_dashboard', service_id=service_one['id'])

    flask_session.pop('invited_user_id')

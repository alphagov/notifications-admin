import pytest
from flask import url_for

from tests.conftest import (
    SERVICE_ONE_ID,
    normalize_spaces,
    set_config,
    url_for_endpoint_with_token,
)


@pytest.fixture
def mock_email_validated_recently(mocker):
    return mocker.patch('app.main.views.two_factor.email_needs_revalidating', return_value=False)


@pytest.mark.parametrize('request_url', ['two_factor_email_sent', 'revalidate_email_sent'])
@pytest.mark.parametrize('redirect_url', [None, f'/services/{SERVICE_ONE_ID}/templates'])
@pytest.mark.parametrize('email_resent, page_title', [
    (None, 'Check your email'),
    (True, 'Email resent')
])
def test_two_factor_email_sent_page(
    client_request,
    email_resent,
    page_title,
    redirect_url,
    request_url
):
    client_request.logout()
    page = client_request.get(
        f'main.{request_url}',
        next=redirect_url,
        email_resent=email_resent,
    )

    assert page.h1.string == page_title
    # there shouldn't be a form for updating mobile number
    assert page.find('form') is None
    resend_email_link = page.find('a', class_="govuk-link govuk-link--no-visited-state page-footer-secondary-link")
    assert resend_email_link.text == 'Not received an email?'
    assert resend_email_link['href'] == url_for('main.email_not_received', next=redirect_url)


@pytest.mark.parametrize('redirect_url', [
    None,
    f'/services/{SERVICE_ONE_ID}/templates',
])
def test_should_render_two_factor_page(
    client_request,
    api_user_active,
    mock_get_user_by_email,
    mocker,
    redirect_url
):
    client_request.logout()
    # TODO this lives here until we work out how to
    # reassign the session after it is lost mid register process
    with client_request.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address']}
    mocker.patch('app.user_api_client.get_user', return_value=api_user_active)
    page = client_request.get('main.two_factor_sms', next=redirect_url)

    assert page.select_one('main p').text.strip() == (
        'We’ve sent you a text message with a security code.'
    )
    assert page.select_one('label').text.strip() == (
        'Text message code'
    )
    assert page.select_one('input')['type'] == 'tel'
    assert page.select_one('input')['pattern'] == '[0-9]*'

    assert page.select_one(
        'a:contains("Not received a text message?")'
    )['href'] == url_for('main.check_and_resend_text_code', next=redirect_url)


def test_should_login_user_and_should_redirect_to_next_url(
    client_request,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_check_verify_code,
    mock_create_event,
    mock_email_validated_recently,
):
    client_request.logout()

    with client_request.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address']}

    client_request.post(
        'main.two_factor_sms',
        next='/services/{}'.format(SERVICE_ONE_ID),
        _data={'sms_code': '12345'},
        _expected_redirect=url_for(
            'main.service_dashboard',
            service_id=SERVICE_ONE_ID,
        ),
    )


def test_should_send_email_and_redirect_to_info_page_if_user_needs_to_revalidate_email(
    client_request,
    api_user_active,
    mock_get_user,
    mock_check_verify_code,
    mock_create_event,
    mock_send_verify_code,
    mocker
):
    client_request.logout()

    mocker.patch('app.user_api_client.get_user', return_value=api_user_active)
    mocker.patch('app.main.views.two_factor.email_needs_revalidating', return_value=True)
    with client_request.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address']}
    client_request.post(
        'main.two_factor_sms',
        next=f'/services/{SERVICE_ONE_ID}',
        _data={'sms_code': '12345'},
        _expected_redirect=url_for(
            'main.revalidate_email_sent',
            next=f'/services/{SERVICE_ONE_ID}'
        ),
    )

    mock_send_verify_code.assert_called_with(api_user_active['id'], 'email', None, mocker.ANY)


def test_should_login_user_and_not_redirect_to_external_url(
    client_request,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_check_verify_code,
    mock_get_services_with_one_service,
    mock_create_event,
    mock_email_validated_recently,
):
    client_request.logout()

    with client_request.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address']}

    client_request.post(
        'main.two_factor_sms',
        next='http://www.google.com',
        _data={'sms_code': '12345'},
        _expected_redirect=url_for('main.show_accounts_or_dashboard')
    )


@pytest.mark.parametrize('platform_admin', (
    True, False,
))
def test_should_login_user_and_redirect_to_show_accounts(
    client_request,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_check_verify_code,
    mock_create_event,
    mock_email_validated_recently,
    platform_admin,
):
    client_request.logout()

    with client_request.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address']}
    api_user_active['platform_admin'] = platform_admin

    client_request.post(
        'main.two_factor_sms',
        _data={'sms_code': '12345'},
        _expected_redirect=url_for('main.show_accounts_or_dashboard')
    )


def test_should_return_200_with_sms_code_error_when_sms_code_is_wrong(
    client_request,
    api_user_active,
    mock_get_user_by_email,
    mock_check_verify_code_code_not_found,
    mocker
):
    client_request.logout()

    with client_request.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address']}
    mocker.patch('app.user_api_client.get_user', return_value=api_user_active)

    page = client_request.post(
        'main.two_factor_sms',
        _data={'sms_code': '23456'},
        _expected_status=200,
    )
    assert 'Code not found' in page.text


def test_should_login_user_when_multiple_valid_codes_exist(
    client_request,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_check_verify_code,
    mock_get_services_with_one_service,
    mock_create_event,
    mock_email_validated_recently,
):
    client_request.logout()

    with client_request.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address']}

    client_request.post(
        'main.two_factor_sms',
        _data={'sms_code': '23456'},
        _expected_status=302,
    )


def test_two_factor_sms_should_set_password_when_new_password_exists_in_session(
    client_request,
    api_user_active,
    mock_get_user,
    mock_check_verify_code,
    mock_get_services_with_one_service,
    mock_update_user_password,
    mock_create_event,
    mock_email_validated_recently,
):
    client_request.logout()

    with client_request.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_active['id'],
            'email': api_user_active['email_address'],
            'password': 'changedpassword'}

    client_request.post(
        'main.two_factor_sms',
        _data={'sms_code': '12345'},
        _expected_redirect=url_for('main.show_accounts_or_dashboard'),
    )

    mock_update_user_password.assert_called_once_with(
        api_user_active['id'], 'changedpassword',
    )


def test_two_factor_sms_returns_error_when_user_is_locked(
    client_request,
    api_user_locked,
    mock_get_locked_user,
    mock_check_verify_code_code_not_found,
    mock_get_services_with_one_service
):
    client_request.logout()

    with client_request.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_locked['id'],
            'email': api_user_locked['email_address'],
        }
    page = client_request.post(
        'main.two_factor_sms',
        _data={'sms_code': '12345'},
        _expected_status=200,
    )
    assert 'Code not found' in page.text


def test_two_factor_sms_post_should_redirect_to_sign_in_if_user_not_in_session(
    client_request,
):
    client_request.post(
        'main.two_factor_sms',
        _data={'sms_code': '12345'},
        _expected_redirect=url_for('main.sign_in')
    )


@pytest.mark.parametrize('endpoint', ['main.two_factor_webauthn', 'main.two_factor_sms'])
def test_two_factor_endpoints_get_should_redirect_to_sign_in_if_user_not_in_session(
    client_request,
    endpoint,
):
    client_request.get(
        endpoint,
        _expected_redirect=url_for('main.sign_in')
    )


def test_two_factor_webauthn_should_have_auth_signin_button(
    client_request,
    platform_admin_user,
    mocker,
):
    client_request.logout()
    mock_get_user = mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
    with client_request.session_transaction() as session:
        session['user_details'] = {'id': platform_admin_user['id'], 'email': platform_admin_user['email_address']}

    page = client_request.get('main.two_factor_webauthn')

    button = page.select_one("button[data-module=authenticate-security-key]")

    assert button.text.strip() == 'Check security key'

    assert button.name == 'button'
    mock_get_user.assert_called_once_with(platform_admin_user['id'])


def test_two_factor_webauthn_should_reject_non_webauthn_auth_users(
    client_request,
    platform_admin_user,
    mocker,
):
    client_request.logout()
    platform_admin_user['auth_type'] = 'sms_auth'
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
    with client_request.session_transaction() as session:
        session['user_details'] = {'id': platform_admin_user['id'], 'email': platform_admin_user['email_address']}

    client_request.get(
        'main.two_factor_webauthn',
        _expected_status=403,
    )


def test_two_factor_sms_should_activate_pending_user(
    client_request,
    mocker,
    api_user_pending,
    mock_check_verify_code,
    mock_create_event,
    mock_activate_user,
    mock_email_validated_recently,
):
    client_request.logout()
    mocker.patch('app.user_api_client.get_user', return_value=api_user_pending)
    mocker.patch('app.service_api_client.get_services', return_value={'data': []})
    with client_request.session_transaction() as session:
        session['user_details'] = {
            'id': api_user_pending['id'],
            'email_address': api_user_pending['email_address']
        }
    client_request.post('main.two_factor_sms', _data={'sms_code': '12345'})

    assert mock_activate_user.called


@pytest.mark.parametrize('extra_args, expected_encoded_next_arg', (
    ({}, ''),
    ({'next': 'https://example.com'}, '?next=https%3A%2F%2Fexample.com')
))
def test_valid_two_factor_email_link_shows_interstitial(
    client_request,
    valid_token,
    mocker,
    extra_args,
    expected_encoded_next_arg,
):
    mock_check_code = mocker.patch('app.user_api_client.check_verify_code')
    encoded_token = valid_token.replace('%2E', '.')
    token_url = url_for(
        'main.two_factor_email_interstitial',
        token=encoded_token,
        **extra_args
    )

    # This must match the URL we put in the emails
    assert token_url == f'/email-auth/{encoded_token}{expected_encoded_next_arg}'

    client_request.logout()
    page = client_request.get_url(token_url)

    assert normalize_spaces(page.select_one('main .js-hidden').text) == (
        'Sign in '
        'Continue to dashboard'
    )

    form = page.select_one('form')
    expected_form_id = 'use-email-auth'
    assert 'action' not in form
    assert form['method'] == 'post'
    assert form['id'] == expected_form_id
    assert page.select_one('main script').string.strip() == (
        f'document.getElementById("{expected_form_id}").submit();'
    )

    assert mock_check_code.called is False


def test_valid_two_factor_email_link_logs_in_user(
    client_request,
    valid_token,
    mock_get_user,
    mock_get_services_with_one_service,
    mocker,
    mock_create_event,
):
    mocker.patch('app.user_api_client.check_verify_code', return_value=(True, ''))

    client_request.post_url(
        url_for_endpoint_with_token('main.two_factor_email', token=valid_token),
        _expected_redirect=url_for('main.show_accounts_or_dashboard')
    )


@pytest.mark.parametrize('redirect_url', [
    None,
    f'/services/{SERVICE_ONE_ID}/templates',
])
def test_two_factor_email_link_has_expired(
    notify_admin,
    valid_token,
    client_request,
    mock_send_verify_code,
    fake_uuid,
    redirect_url
):
    client_request.logout()

    with set_config(notify_admin, 'EMAIL_2FA_EXPIRY_SECONDS', -1):
        page = client_request.post_url(
            url_for_endpoint_with_token('main.two_factor_email', token=valid_token, next=redirect_url),
            _follow_redirects=True,
        )

    assert page.h1.text.strip() == 'The link has expired'
    assert page.select_one('a:contains("Sign in again")')['href'] == url_for('main.sign_in', next=redirect_url)

    assert mock_send_verify_code.called is False


def test_two_factor_email_link_is_invalid(
    client_request
):
    client_request.logout()
    token = 12345
    page = client_request.post(
        'main.two_factor_email',
        token=token,
        _follow_redirects=True,
        _expected_status=404,
    )

    assert normalize_spaces(
        page.select_one('.banner-dangerous').text
    ) == "There’s something wrong with the link you’ve used."


@pytest.mark.parametrize('redirect_url', [
    None,
    f'/services/{SERVICE_ONE_ID}/templates',
])
def test_two_factor_email_link_is_already_used(
    client_request,
    valid_token,
    mocker,
    mock_send_verify_code,
    redirect_url

):
    client_request.logout()
    mocker.patch('app.user_api_client.check_verify_code', return_value=(False, 'Code has expired'))

    page = client_request.post_url(
        url_for_endpoint_with_token('main.two_factor_email', token=valid_token, next=redirect_url),
        _follow_redirects=True,
    )

    assert page.h1.text.strip() == 'The link has expired'
    assert page.select_one('a:contains("Sign in again")')['href'] == url_for('main.sign_in', next=redirect_url)

    assert mock_send_verify_code.called is False


def test_two_factor_email_link_when_user_is_locked_out(
    client_request,
    valid_token,
    mocker,
    mock_send_verify_code
):
    client_request.logout()
    mocker.patch('app.user_api_client.check_verify_code', return_value=(False, 'Code not found'))

    page = client_request.post_url(
        url_for_endpoint_with_token('main.two_factor_email', token=valid_token),
        _follow_redirects=True,
    )

    assert page.h1.text.strip() == 'The link has expired'
    assert mock_send_verify_code.called is False


def test_two_factor_email_link_used_when_user_already_logged_in(
    client_request,
    valid_token
):
    client_request.post_url(
        url_for_endpoint_with_token('main.two_factor_email', token=valid_token),
        _expected_redirect=url_for('main.show_accounts_or_dashboard'),
    )

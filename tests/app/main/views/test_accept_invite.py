from flask import url_for
from bs4 import BeautifulSoup
from unittest.mock import ANY
from itsdangerous import SignatureExpired

import app

from app.notify_client.models import InvitedUser
from tests.conftest import sample_invite as create_sample_invite
from tests.conftest import mock_check_invite_token as mock_check_token_invite


def test_existing_user_accept_invite_calls_api_and_redirects_to_dashboard(
    client,
    service_one,
    api_user_active,
    mock_check_invite_token,
    mock_get_user_by_email,
    mock_get_users_by_service,
    mock_accept_invite,
    mock_add_user_to_service,
    mocker,
):
    mocker.patch('app.main.views.invites.check_token')

    expected_service = service_one['id']
    expected_redirect_location = 'http://localhost/services/{}/dashboard'.format(expected_service)
    expected_permissions = ['send_messages', 'manage_service', 'manage_api_keys']

    response = client.get(url_for('main.accept_invite', token='thisisnotarealtoken'))

    mock_check_invite_token.assert_called_with('thisisnotarealtoken')
    mock_get_user_by_email.assert_called_with('invited_user@test.gov.uk')
    assert mock_accept_invite.call_count == 1
    mock_add_user_to_service.assert_called_with(expected_service, api_user_active.id, expected_permissions)

    assert response.status_code == 302
    assert response.location == expected_redirect_location


def test_existing_user_with_no_permissions_accept_invite(
    client,
    mocker,
    service_one,
    api_user_active,
    sample_invite,
    mock_check_invite_token,
    mock_get_user_by_email,
    mock_get_users_by_service,
    mock_add_user_to_service,
):
    mocker.patch('app.main.views.invites.check_token')

    expected_service = service_one['id']
    sample_invite['permissions'] = ''
    expected_permissions = []
    mocker.patch('app.invite_api_client.accept_invite', return_value=sample_invite)

    response = client.get(url_for('main.accept_invite', token='thisisnotarealtoken'))
    mock_add_user_to_service.assert_called_with(expected_service, api_user_active.id, expected_permissions)

    assert response.status_code == 302


def test_if_existing_user_accepts_twice_they_redirect_to_sign_in(
    client,
    mocker,
    sample_invite,
    mock_get_service,
):
    mocker.patch('app.main.views.invites.check_token')

    sample_invite['status'] = 'accepted'
    invite = InvitedUser(**sample_invite)
    mocker.patch('app.invite_api_client.check_token', return_value=invite)

    response = client.get(url_for('main.accept_invite', token='thisisnotarealtoken'), follow_redirects=True)
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert (
        page.h1.string,
        page.select('main p')[0].text.strip(),
    ) == (
        'You need to sign in again',
        'We signed you out because you haven’t used Notify for a while.',
    )


def test_existing_user_of_service_get_redirected_to_signin(
    client,
    mocker,
    api_user_active,
    sample_invite,
    mock_get_service,
    mock_get_user_by_email,
    mock_accept_invite,
):
    mocker.patch('app.main.views.invites.check_token')
    sample_invite['email_address'] = api_user_active.email_address
    invite = InvitedUser(**sample_invite)
    mocker.patch('app.invite_api_client.check_token', return_value=invite)
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[api_user_active])

    response = client.get(url_for('main.accept_invite', token='thisisnotarealtoken'), follow_redirects=True)
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert (
        page.h1.string,
        page.select('main p')[0].text.strip(),
    ) == (
        'You need to sign in again',
        'We signed you out because you haven’t used Notify for a while.',
    )
    assert mock_accept_invite.call_count == 1


def test_existing_signed_out_user_accept_invite_redirects_to_sign_in(
    client,
    service_one,
    api_user_active,
    sample_invite,
    mock_check_invite_token,
    mock_get_user_by_email,
    mock_get_users_by_service,
    mock_add_user_to_service,
    mock_accept_invite,
    mock_get_service,
    mocker,
):
    mocker.patch('app.main.views.invites.check_token')

    expected_service = service_one['id']
    expected_permissions = ['send_messages', 'manage_service', 'manage_api_keys']

    response = client.get(url_for('main.accept_invite', token='thisisnotarealtoken'), follow_redirects=True)

    mock_check_invite_token.assert_called_with('thisisnotarealtoken')
    mock_get_user_by_email.assert_called_with('invited_user@test.gov.uk')
    mock_add_user_to_service.assert_called_with(expected_service, api_user_active.id, expected_permissions)
    assert mock_accept_invite.call_count == 1

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert (
        page.h1.string,
        page.select('main p')[0].text.strip(),
    ) == (
        'You need to sign in again',
        'We signed you out because you haven’t used Notify for a while.',
    )


def test_new_user_accept_invite_calls_api_and_redirects_to_registration(
    client,
    service_one,
    mock_check_invite_token,
    mock_dont_get_user_by_email,
    mock_add_user_to_service,
    mock_get_users_by_service,
    mock_get_service,
    mocker,
):
    mocker.patch('app.main.views.invites.check_token')

    expected_redirect_location = 'http://localhost/register-from-invite'

    response = client.get(url_for('main.accept_invite', token='thisisnotarealtoken'))

    mock_check_invite_token.assert_called_with('thisisnotarealtoken')
    mock_dont_get_user_by_email.assert_called_with('invited_user@test.gov.uk')

    assert response.status_code == 302
    assert response.location == expected_redirect_location


def test_new_user_accept_invite_calls_api_and_views_registration_page(
    client,
    service_one,
    mock_check_invite_token,
    mock_dont_get_user_by_email,
    mock_add_user_to_service,
    mock_get_users_by_service,
    mock_get_service,
    mocker,
):
    mocker.patch('app.main.views.invites.check_token')

    response = client.get(url_for('main.accept_invite', token='thisisnotarealtoken'), follow_redirects=True)

    mock_check_invite_token.assert_called_with('thisisnotarealtoken')
    mock_dont_get_user_by_email.assert_called_with('invited_user@test.gov.uk')

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string.strip() == 'Create an account'

    email_in_page = page.find('main').find('p')
    assert email_in_page.text.strip() == 'Your account will be created with this email: invited_user@test.gov.uk'  # noqa

    form = page.find('form')
    name = form.find('input', id='name')
    password = form.find('input', id='password')
    service = form.find('input', type='hidden', id='service')
    email = form.find('input', type='hidden', id='email_address')

    assert email
    assert email.attrs['value'] == 'invited_user@test.gov.uk'
    assert name
    assert password
    assert service
    assert service.attrs['value'] == service_one['id']


def test_cancelled_invited_user_accepts_invited_redirect_to_cancelled_invitation(
    client,
    service_one,
    mocker,
    mock_get_user,
    mock_get_service,
):
    mocker.patch('app.main.views.invites.check_token')
    cancelled_invitation = create_sample_invite(mocker, service_one, status='cancelled')
    mock_check_token_invite(mocker, cancelled_invitation)
    response = client.get(url_for('main.accept_invite', token='thisisnotarealtoken'))

    app.invite_api_client.check_token.assert_called_with('thisisnotarealtoken')
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string.strip() == 'The invitation you were sent has been cancelled'


def test_new_user_accept_invite_completes_new_registration_redirects_to_verify(
    client,
    service_one,
    sample_invite,
    api_user_active,
    mock_check_invite_token,
    mock_dont_get_user_by_email,
    mock_is_email_unique,
    mock_register_user,
    mock_send_verify_code,
    mock_accept_invite,
    mock_get_users_by_service,
    mock_add_user_to_service,
    mock_get_service,
    mocker,
):
    mocker.patch('app.main.views.invites.check_token')

    expected_service = service_one['id']
    expected_email = sample_invite['email_address']
    expected_from_user = service_one['users'][0]
    expected_redirect_location = 'http://localhost/register-from-invite'

    response = client.get(url_for('main.accept_invite', token='thisisnotarealtoken'))
    with client.session_transaction() as session:
        assert response.status_code == 302
        assert response.location == expected_redirect_location
        invited_user = session.get('invited_user')
        assert invited_user
        assert expected_service == invited_user['service']
        assert expected_email == invited_user['email_address']
        assert expected_from_user == invited_user['from_user']

    data = {'service': invited_user['service'],
            'email_address': invited_user['email_address'],
            'from_user': invited_user['from_user'],
            'password': 'longpassword',
            'mobile_number': '+447890123456',
            'name': 'Invited User',
            'auth_type': 'email_auth'
            }

    expected_redirect_location = 'http://localhost/verify'
    response = client.post(url_for('main.register_from_invite'), data=data)
    assert response.status_code == 302
    assert response.location == expected_redirect_location

    mock_send_verify_code.assert_called_once_with(ANY, 'sms', data['mobile_number'])

    mock_register_user.assert_called_with(data['name'],
                                          data['email_address'],
                                          data['mobile_number'],
                                          data['password'],
                                          data['auth_type'])

    assert mock_accept_invite.call_count == 1


def test_signed_in_existing_user_cannot_use_anothers_invite(
    logged_in_client,
    mocker,
    api_user_active,
    sample_invite,
    mock_get_user,
    mock_accept_invite,
    mock_get_service,
):
    mocker.patch('app.main.views.invites.check_token')
    invite = InvitedUser(**sample_invite)
    mocker.patch('app.invite_api_client.check_token', return_value=invite)
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[api_user_active])

    response = logged_in_client.get(url_for('main.accept_invite', token='thisisnotarealtoken'), follow_redirects=True)
    assert response.status_code == 403
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string.strip() == '403'
    flash_banners = page.find_all('div', class_='banner-dangerous')
    assert len(flash_banners) == 1
    banner_contents = flash_banners[0].text.strip()
    assert "You’re signed in as test@user.gov.uk." in banner_contents
    assert "This invite is for another email address." in banner_contents
    assert "Sign out and click the link again to accept this invite." in banner_contents
    assert mock_accept_invite.call_count == 0


def test_gives_message_if_token_has_expired(
    app_,
    client,
    mock_check_invite_token,
    mocker,
):
    check_token = mocker.patch('app.main.views.invites.check_token', side_effect=SignatureExpired('this is too old'))

    response = client.get(url_for('main.accept_invite', token='a really old token'))
    raw_html = response.data.decode('utf-8')
    page = BeautifulSoup(raw_html, 'html.parser')

    check_token.assert_called_once_with(ANY, ANY, ANY, 3600 * 24 * 2)
    assert response.status_code == 400
    assert 'Your invitation to GOV.UK Notify has expired' in page.find('h1').text
    assert not mock_check_invite_token.called

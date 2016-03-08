from flask import url_for

from bs4 import BeautifulSoup

import app
from tests.conftest import sample_invite as create_sample_invite
from tests.conftest import mock_check_invite_token as mock_check_token_invite


def test_existing_user_accept_invite_calls_api_and_redirects_to_dashboard(app_,
                                                                          service_one,
                                                                          api_user_active,
                                                                          sample_invite,
                                                                          mock_check_invite_token,
                                                                          mock_get_user_by_email,
                                                                          mock_add_user_to_service,
                                                                          mock_accept_invite):

    expected_service = service_one['id']
    expected_redirect_location = 'http://localhost/services/{}/dashboard'.format(expected_service)
    expected_permissions = ['send_messages', 'manage_service', 'manage_api_keys']

    with app_.test_request_context():
        with app_.test_client() as client:

            response = client.get(url_for('main.accept_invite', token='thisisnotarealtoken'))

            mock_check_invite_token.assert_called_with('thisisnotarealtoken')
            mock_get_user_by_email.assert_called_with('invited_user@test.gov.uk')
            mock_add_user_to_service.assert_called_with(expected_service, api_user_active.id, expected_permissions)
            mock_accept_invite.assert_called_with(expected_service, sample_invite['id'])

            assert response.status_code == 302
            assert response.location == expected_redirect_location


def test_existing_signed_out_user_accept_invite_redirects_to_sign_in(app_,
                                                                     service_one,
                                                                     api_user_active,
                                                                     sample_invite,
                                                                     mock_check_invite_token,
                                                                     mock_get_user_by_email,
                                                                     mock_add_user_to_service,
                                                                     mock_accept_invite):

    expected_service = service_one['id']
    expected_permissions = ['send_messages', 'manage_service', 'manage_api_keys']
    with app_.test_request_context():
        with app_.test_client() as client:

            response = client.get(url_for('main.accept_invite', token='thisisnotarealtoken'), follow_redirects=True)

            mock_check_invite_token.assert_called_with('thisisnotarealtoken')
            mock_get_user_by_email.assert_called_with('invited_user@test.gov.uk')
            mock_add_user_to_service.assert_called_with(expected_service, api_user_active.id, expected_permissions)
            mock_accept_invite.assert_called_with(expected_service, sample_invite['id'])

            assert response.status_code == 200
            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
            assert page.h1.string.strip() == 'Sign in'


def test_new_user_accept_invite_calls_api_and_redirects_to_registration(app_,
                                                                        service_one,
                                                                        mock_check_invite_token,
                                                                        mock_dont_get_user_by_email,
                                                                        mock_add_user_to_service,
                                                                        mock_accept_invite):

    expected_redirect_location = 'http://localhost/register-from-invite'

    with app_.test_request_context():
        with app_.test_client() as client:

            response = client.get(url_for('main.accept_invite', token='thisisnotarealtoken'))

            mock_check_invite_token.assert_called_with('thisisnotarealtoken')
            mock_dont_get_user_by_email.assert_called_with('invited_user@test.gov.uk')

            assert response.status_code == 302
            assert response.location == expected_redirect_location


def test_new_user_accept_invite_calls_api_and_views_registration_page(app_,
                                                                      service_one,
                                                                      mock_check_invite_token,
                                                                      mock_dont_get_user_by_email,
                                                                      mock_add_user_to_service,
                                                                      mock_accept_invite):

    with app_.test_request_context():
        with app_.test_client() as client:

            response = client.get(url_for('main.accept_invite', token='thisisnotarealtoken'), follow_redirects=True)

            mock_check_invite_token.assert_called_with('thisisnotarealtoken')
            mock_dont_get_user_by_email.assert_called_with('invited_user@test.gov.uk')

            assert response.status_code == 200
            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
            assert page.h1.string.strip() == 'Create an account'

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


def test_cancelled_invited_user_accepts_invited_redirect_to_cancelled_invitation(app_,
                                                                                 service_one,
                                                                                 mocker,
                                                                                 mock_get_user,
                                                                                 mock_get_service
                                                                                 ):
    with app_.test_request_context():
        with app_.test_client() as client:
            cancelled_invitation = create_sample_invite(mocker, service_one, status='cancelled')
            mock_check_token_invite(mocker, cancelled_invitation)
            response = client.get(url_for('main.accept_invite', token='thisisnotarealtoken'))

            app.invite_api_client.check_token.assert_called_with('thisisnotarealtoken')
            assert response.status_code == 200
            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
            assert page.h1.string.strip() == 'The invitation you were sent has been cancelled'


def test_new_user_accept_invite_completes_new_registration_redirects_to_verify(app_,
                                                                               service_one,
                                                                               sample_invite,
                                                                               mock_check_invite_token,
                                                                               mock_dont_get_user_by_email,
                                                                               mock_register_user,
                                                                               mock_send_verify_code,
                                                                               mock_add_user_to_service,
                                                                               mock_accept_invite):

    expected_service = service_one['id']
    expected_email = sample_invite['email_address']
    expected_from_user = service_one['users'][0]
    expected_redirect_location = 'http://localhost/register-from-invite'

    with app_.test_request_context():
        with app_.test_client() as client:
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
                    'name': 'Invited User'
                    }

            expected_redirect_location = 'http://localhost/verify'
            response = client.post(url_for('main.register_from_invite'), data=data)
            assert response.status_code == 302
            assert response.location == expected_redirect_location

            mock_register_user.assert_called_with(data['name'],
                                                  data['email_address'],
                                                  data['mobile_number'],
                                                  data['password'])


def test_new_invited_user_verifies_and_added_to_service(app_,
                                                        service_one,
                                                        sample_invite,
                                                        mock_check_invite_token,
                                                        mock_dont_get_user_by_email,
                                                        mock_register_user,
                                                        mock_send_verify_code,
                                                        mock_check_verify_code,
                                                        mock_get_user,
                                                        mock_update_user,
                                                        mock_add_user_to_service,
                                                        mock_accept_invite,
                                                        mock_get_service,
                                                        mock_get_service_templates,
                                                        mock_get_jobs):

    with app_.test_request_context():
        with app_.test_client() as client:
            # visit accept token page
            response = client.get(url_for('main.accept_invite', token='thisisnotarealtoken'))
            data = {'service': sample_invite['service'],
                    'email_address': sample_invite['email_address'],
                    'from_user': sample_invite['from_user'],
                    'password': 'longpassword',
                    'mobile_number': '+447890123456',
                    'name': 'Invited User'
                    }

            # get redirected to register from invite
            response = client.post(url_for('main.register_from_invite'), data=data)

            # that sends user on to verify
            response = client.post(url_for('main.verify'), data={'sms_code': '12345', 'email_code': '23456'},
                                   follow_redirects=True)

            # when they post codes back to admin user should be added to
            # service and sent on to dash board
            expected_permissions = ['send_messages', 'manage_service', 'manage_api_keys']
            with client.session_transaction() as session:
                new_user_id = session['user_id']
                mock_add_user_to_service.assert_called_with(data['service'], new_user_id, expected_permissions)

            mock_accept_invite.assert_called_with(data['service'], sample_invite['id'])

            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
            element = page.find('h2', class_='navigation-service-name').find('a')
            assert element.text == 'Test Service'
            service_link = element.attrs['href']
            assert service_link == '/services/{}/dashboard'.format(service_one['id'])

            flash_banner = page.find('div', class_='banner-default-with-tick').string.strip()
            assert flash_banner == 'You have sucessfully accepted your invitation and been added to Test Service'

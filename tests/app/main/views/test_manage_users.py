from flask import url_for
from bs4 import BeautifulSoup
import app
from app.notify_client.models import InvitedUser
from tests.conftest import service_one as service_1


def test_should_show_overview_page(
    app_,
    active_user_with_permissions,
    mocker,
    mock_get_invites_for_service
):
    service = service_1(active_user_with_permissions)
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service)
            mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])
            response = client.get(url_for('main.manage_users', service_id=service['id']))

        assert 'Team members' in response.get_data(as_text=True)
        assert response.status_code == 200
        app.user_api_client.get_users_for_service.assert_called_once_with(service_id=service['id'])


def test_should_show_page_for_one_user(
    app_,
    active_user_with_permissions,
    mocker
):
    service = service_1(active_user_with_permissions)
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service)
            response = client.get(url_for('main.edit_user_permissions', service_id=service['id'], user_id=0))

        assert response.status_code == 200


def test_edit_user_permissions(
    app_,
    active_user_with_permissions,
    mocker,
    mock_get_invites_for_service,
    mock_set_user_permissions
):
    service = service_1(active_user_with_permissions)
    with app_.test_request_context():
        with app_.test_client() as client:

            client.login(active_user_with_permissions, mocker, service)
            response = client.post(url_for(
                'main.edit_user_permissions', service_id=service['id'], user_id=active_user_with_permissions.id
            ), data={'email_address': active_user_with_permissions.email_address,
                     'send_messages': 'y',
                     'manage_service': 'y',
                     'manage_api_keys': 'y'})

        assert response.status_code == 302
        assert response.location == url_for(
            'main.manage_users', service_id=service['id'], _external=True
        )
        mock_set_user_permissions.assert_called_with(
            str(active_user_with_permissions.id),
            service['id'],
            permissions={
                'send_texts',
                'send_emails',
                'send_letters',
                'manage_users',
                'manage_templates',
                'manage_settings',
                'manage_api_keys',
                'view_activity'
            }
        )


def test_edit_some_user_permissions(
    app_,
    mocker,
    active_user_with_permissions,
    sample_invite,
    mock_get_invites_for_service,
    mock_set_user_permissions
):
    service = service_1(active_user_with_permissions)
    data = [InvitedUser(**sample_invite)]
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service)
            service_id = service['id']

            mocker.patch('app.invite_api_client.get_invites_for_service', return_value=data)
            response = client.post(url_for(
                'main.edit_user_permissions', service_id=service_id, user_id=active_user_with_permissions.id
            ), data={'email_address': active_user_with_permissions.email_address,
                     'send_messages': 'y',
                     'manage_service': '',
                     'manage_api_keys': ''})

        assert response.status_code == 302
        assert response.location == url_for(
            'main.manage_users', service_id=service_id, _external=True
        )
        mock_set_user_permissions.assert_called_with(
            str(active_user_with_permissions.id),
            service_id,
            permissions={
                'send_texts',
                'send_emails',
                'send_letters',
                'view_activity'
            }
        )


def test_should_show_page_for_inviting_user(
    app_,
    active_user_with_permissions,
    mocker
):
    service = service_1(active_user_with_permissions)
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service)
            response = client.get(url_for('main.invite_user', service_id=service['id']))

        assert 'Invite a team member' in response.get_data(as_text=True)
        assert response.status_code == 200


def test_invite_user(
    app_,
    active_user_with_permissions,
    mocker,
    sample_invite
):
    service = service_1(active_user_with_permissions)
    email_address = 'test@example.gov.uk'
    sample_invite['email_address'] = 'test@example.gov.uk'

    data = [InvitedUser(**sample_invite)]
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service)
            mocker.patch('app.invite_api_client.get_invites_for_service', return_value=data)
            mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])
            mocker.patch('app.invite_api_client.create_invite', return_value=InvitedUser(**sample_invite))
            response = client.post(
                url_for('main.invite_user', service_id=service['id']),
                data={'email_address': email_address,
                      'send_messages': 'y',
                      'manage_service': 'y',
                      'manage_api_keys': 'y'},
                follow_redirects=True
            )

        assert response.status_code == 200
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.h1.string.strip() == 'Team members'
        flash_banner = page.find('div', class_='banner-default-with-tick').string.strip()
        assert flash_banner == 'Invite sent to test@example.gov.uk'
        excpected_permissions = 'manage_api_keys,manage_service,send_messages,view_activity'
        app.invite_api_client.create_invite.assert_called_once_with(sample_invite['from_user'],
                                                                    sample_invite['service'],
                                                                    email_address,
                                                                    excpected_permissions)


def test_cancel_invited_user_cancels_user_invitations(app_,
                                                      active_user_with_permissions,
                                                      mocker
                                                      ):
    with app_.test_request_context():
        with app_.test_client() as client:
            mocker.patch('app.invite_api_client.cancel_invited_user')
            import uuid
            invited_user_id = uuid.uuid4()
            service = service_1(active_user_with_permissions)
            client.login(active_user_with_permissions, mocker, service)
            response = client.get(url_for('main.cancel_invited_user', service_id=service['id'],
                                          invited_user_id=invited_user_id))

            assert response.status_code == 302
            assert response.location == url_for('main.manage_users', service_id=service['id'], _external=True)


def test_manage_users_shows_invited_user(app_,
                                         mocker,
                                         active_user_with_permissions,
                                         sample_invite):
    service = service_1(active_user_with_permissions)
    data = [InvitedUser(**sample_invite)]
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service)

            mocker.patch('app.invite_api_client.get_invites_for_service', return_value=data)
            mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])

            response = client.get(url_for('main.manage_users', service_id=service['id']))

            assert response.status_code == 200
            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
            assert page.h1.string.strip() == 'Team members'
            invites_table = page.find_all('table')[1]
            cols = invites_table.find_all('td')
            assert cols[0].text.strip() == 'invited_user@test.gov.uk'
            assert cols[4].text.strip() == 'Cancel invitation'


def test_manage_users_does_not_show_accepted_invite(app_,
                                                    mocker,
                                                    active_user_with_permissions,
                                                    sample_invite):

    import uuid
    invited_user_id = uuid.uuid4()
    sample_invite['id'] = invited_user_id
    sample_invite['status'] = 'accepted'
    data = [InvitedUser(**sample_invite)]
    service = service_1(active_user_with_permissions)
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service)
            mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])
            mocker.patch('app.invite_api_client.get_invites_for_service', return_value=data)

            response = client.get(url_for('main.manage_users', service_id=service['id']))

            assert response.status_code == 200
            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
            assert page.h1.string.strip() == 'Team members'
            tables = page.find_all('table')
            assert len(tables) == 1
            assert not page.find(text='invited_user@test.gov.uk')


def test_user_cant_invite_themselves(
    app_,
    mocker,
    active_user_with_permissions,
    mock_create_invite
):
    service = service_1(active_user_with_permissions)
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service)
            response = client.post(
                url_for('main.invite_user', service_id=service['id']),
                data={'email_address': active_user_with_permissions.email_address,
                      'send_messages': 'y',
                      'manage_service': 'y',
                      'manage_api_keys': 'y'},
                follow_redirects=True
            )

        assert response.status_code == 200
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.h1.string.strip() == 'Invite a team member'
        form_error = page.find('span', class_='error-message').string.strip()
        assert form_error == "You can't send an invitation to yourself"
        assert not mock_create_invite.called


def test_no_permission_manage_users_page(app_,
                                         service_one,
                                         api_user_active,
                                         mocker):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active, mocker, service_one)
            response = client.get(url_for('main.manage_users', service_id=service_one['id']))
            resp_text = response.get_data(as_text=True)
            assert url_for('.invite_user', service_id=service_one['id']) not in resp_text
            assert "Edit permission" not in resp_text
            assert "Team members" not in resp_text


def test_get_remove_user_from_service(app_,
                                      active_user_with_permissions,
                                      service_one,
                                      mocker):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            response = client.get(
                url_for(
                    'main.remove_user_from_service',
                    service_id=service_one['id'],
                    user_id=active_user_with_permissions.id))
            assert response.status_code == 200
            assert "Are you sure you want to remove" in response.get_data(as_text=True)
            assert "Remove user from service" in response.get_data(as_text=True)


def test_remove_user_from_service(app_,
                                  active_user_with_permissions,
                                  service_one,
                                  mocker,
                                  mock_get_users_by_service,
                                  mock_get_user,
                                  mock_remove_user_from_service):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user_with_permissions, mocker, service_one)
            response = client.post(
                url_for(
                    'main.remove_user_from_service',
                    service_id=service_one['id'],
                    user_id=active_user_with_permissions.id))
            assert response.status_code == 302
            assert response.location == url_for(
                'main.manage_users', service_id=service_one['id'], _external=True)
            mock_remove_user_from_service.assert_called_once_with(service_one['id'],
                                                                  str(active_user_with_permissions.id))

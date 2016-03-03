from flask import url_for

from bs4 import BeautifulSoup


def test_should_show_overview_page(
    app_,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_has_permissions
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.manage_users', service_id=55555))

        assert 'Manage team' in response.get_data(as_text=True)
        assert response.status_code == 200
        mock_get_users_by_service.assert_called_once_with(service_id='55555')


def test_should_show_page_for_one_user(
    app_,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_has_permissions
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.edit_user_permissions', service_id=55555, user_id=0))

        assert response.status_code == 200


def test_edit_user_permissions(
    app_,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_has_permissions,
    mock_set_user_permissions
):
    with app_.test_request_context():
        with app_.test_client() as client:
            service_id = '55555'
            client.login(api_user_active)
            response = client.post(url_for(
                'main.edit_user_permissions', service_id=service_id, user_id=api_user_active.id
            ), data={'email_address': api_user_active.email_address,
                     'send_messages': 'yes',
                     'manage_service': 'yes',
                     'manage_api_keys': 'yes'})

        assert response.status_code == 302
        assert response.location == url_for(
            'main.manage_users', service_id=service_id, _external=True
        )
        mock_set_user_permissions.assert_called_with(
            str(api_user_active.id),
            service_id,
            ['send_texts',
             'send_emails',
             'send_letters',
             'manage_users',
             'manage_templates',
             'manage_settings',
             'manage_api_keys',
             'access_developer_docs'])


def test_edit_some_user_permissions(
    app_,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_has_permissions,
    mock_set_user_permissions
):
    with app_.test_request_context():
        with app_.test_client() as client:
            service_id = '55555'
            client.login(api_user_active)
            response = client.post(url_for(
                'main.edit_user_permissions', service_id=service_id, user_id=api_user_active.id
            ), data={'email_address': api_user_active.email_address,
                     'send_messages': 'yes',
                     'manage_service': 'no',
                     'manage_api_keys': 'no'})

        assert response.status_code == 302
        assert response.location == url_for(
            'main.manage_users', service_id=service_id, _external=True
        )
        mock_set_user_permissions.assert_called_with(
            str(api_user_active.id),
            service_id,
            ['send_texts',
             'send_emails',
             'send_letters'])


def test_should_show_page_for_inviting_user(
    app_,
    api_user_active,
    mock_login,
    mock_get_user,
    mock_get_service,
    mock_has_permissions
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.invite_user', service_id=55555))

        assert 'Add a new team member' in response.get_data(as_text=True)
        assert response.status_code == 200


def test_invite_user(
    app_,
    service_one,
    api_user_active,
    mock_login,
    mock_get_user,
    mock_get_service,
    mock_get_users_by_service,
    mock_create_invite,
    mock_get_invites_for_service,
    mock_has_permissions
):
    from_user = api_user_active.id
    service_id = service_one['id']
    email_address = 'test@example.gov.uk'
    permissions = 'send_messages,manage_service,manage_api_keys'

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.post(
                url_for('main.invite_user', service_id=service_id),
                data={'email_address': email_address,
                      'send_messages': 'yes',
                      'manage_service': 'yes',
                      'manage_api_keys': 'yes'},
                follow_redirects=True
            )

        assert response.status_code == 200
        mock_create_invite.assert_called_with(from_user, service_id, email_address, permissions)
        mock_get_invites_for_service.assert_called_with(service_id=service_id)
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.h1.string.strip() == 'Manage team'
        flash_banner = page.find('div', class_='banner-default-with-tick').string.strip()
        assert flash_banner == 'Invite sent to test@example.gov.uk'


def test_cancel_invited_user_cancels_user_invitations(app_,
                                                      api_user_active,
                                                      mock_login,
                                                      mocker,
                                                      mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            mocker.patch('app.invite_api_client.cancel_invited_user')
            import uuid
            invited_user_id = uuid.uuid4()
            client.login(api_user_active)
            service_id = uuid.uuid4()
            response = client.get(url_for('main.cancel_invited_user', service_id=service_id,
                                          invited_user_id=invited_user_id))

            assert response.status_code == 302
            assert response.location == url_for('main.manage_users', service_id=service_id, _external=True)

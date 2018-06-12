import copy

import pytest
from bs4 import BeautifulSoup
from flask import url_for

import app
from app.notify_client.models import InvitedUser
from app.utils import is_gov_user
from tests.conftest import (
    SERVICE_ONE_ID,
    active_caseworking_user,
    active_user_manage_template_permission,
    active_user_no_mobile,
    active_user_view_permissions,
    active_user_with_permissions,
    normalize_spaces,
)
from tests.conftest import service_one as create_sample_service


@pytest.mark.parametrize('user, expected_self_text, expected_coworker_text', [
    (
        active_user_with_permissions,
        (
            'Test User (you) '
            'Can Send messages Can Add and edit templates Can Manage service Can Access API keys'
        ),
        (
            'ZZZZZZZZ zzzzzzz@example.gov.uk '
            'Can’t Send messages Can’t Add and edit templates Can’t Manage service Can’t Access API keys '
            'Edit permissions'
        )
    ),
    (
        active_user_view_permissions,
        (
            'Test User With Permissions (you) '
            'Can’t Send messages Can’t Add and edit templates Can’t Manage service Can’t Access API keys'
        ),
        (
            'ZZZZZZZZ zzzzzzz@example.gov.uk '
            'Can’t Send messages Can’t Add and edit templates Can’t Manage service Can’t Access API keys'
        )
    ),
    (
        active_user_manage_template_permission,
        (
            'Test User With Permissions (you) '
            'Can’t Send messages Can Add and edit templates Can’t Manage service Can’t Access API keys'
        ),
        (
            'ZZZZZZZZ zzzzzzz@example.gov.uk '
            'Can’t Send messages Can’t Add and edit templates Can’t Manage service Can’t Access API keys'
        )
    ),
    (
        active_user_manage_template_permission,
        (
            'Test User With Permissions (you) '
            'Can’t Send messages Can Add and edit templates Can’t Manage service Can’t Access API keys'
        ),
        (
            'ZZZZZZZZ zzzzzzz@example.gov.uk '
            'Can’t Send messages Can’t Add and edit templates Can’t Manage service Can’t Access API keys'
        )
    ),
])
def test_should_show_overview_page(
    client_request,
    mocker,
    mock_get_invites_for_service,
    fake_uuid,
    service_one,
    user,
    expected_self_text,
    expected_coworker_text,
    active_user_view_permissions,
):
    current_user = user(fake_uuid)
    other_user = copy.deepcopy(active_user_view_permissions)
    other_user.email_address = 'zzzzzzz@example.gov.uk'
    other_user.name = 'ZZZZZZZZ'
    other_user.id = 'zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz'

    mocker.patch('app.user_api_client.get_user', return_value=current_user)
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[
        current_user,
        other_user,
    ])

    page = client_request.get('main.manage_users', service_id=SERVICE_ONE_ID)

    assert normalize_spaces(page.select_one('h1').text) == 'Team members'
    assert normalize_spaces(page.select('.user-list-item')[0].text) == expected_self_text
    # [1:5] are invited users
    assert normalize_spaces(page.select('.user-list-item')[6].text) == expected_coworker_text
    app.user_api_client.get_users_for_service.assert_called_once_with(service_id=SERVICE_ONE_ID)


def test_should_show_caseworker_on_overview_page(
    client_request,
    mocker,
    mock_get_invites_for_service,
    fake_uuid,
    service_one,
):
    service_one['permissions'].append('caseworking')
    current_user = active_user_view_permissions(active_user_view_permissions)
    other_user = active_caseworking_user(fake_uuid)
    other_user.email_address = 'zzzzzzz@example.gov.uk'

    mocker.patch('app.user_api_client.get_user', return_value=current_user)
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[
        current_user,
        other_user,
    ])

    page = client_request.get('main.manage_users', service_id=SERVICE_ONE_ID)

    assert normalize_spaces(page.select_one('h1').text) == 'Team members'
    assert normalize_spaces(page.select('.user-list-item')[0].text) == (
        'Test User With Permissions (you) '
        'Can Admin '
        'Can’t Send messages '
        'Can’t Add and edit templates '
        'Can’t Manage service '
        'Can’t Access API keys'
    )
    # [1:5] are invited users
    assert normalize_spaces(page.select('.user-list-item')[6].text) == (
        'Test User zzzzzzz@example.gov.uk '
        'Can Caseworker'
    )


@pytest.mark.parametrize('endpoint, extra_args, service_has_email_auth, auth_options_hidden', [
    (
        'main.edit_user_permissions',
        {'user_id': 0},
        True,
        False
    ),
    (
        'main.edit_user_permissions',
        {'user_id': 0},
        False,
        True
    ),
    (
        'main.invite_user',
        {},
        True,
        False
    ),
    (
        'main.invite_user',
        {},
        False,
        True
    )
])
def test_service_with_no_email_auth_hides_auth_type_options(
    client_request,
    endpoint,
    extra_args,
    service_has_email_auth,
    auth_options_hidden,
    service_one
):
    if service_has_email_auth:
        service_one['permissions'].append('email_auth')
    page = client_request.get(endpoint, service_id=service_one['id'], **extra_args)
    assert (page.find('input', attrs={"name": "login_authentication"}) is None) == auth_options_hidden


@pytest.mark.parametrize('endpoint, extra_args, service_has_caseworking, radio_buttons_on_page', [
    (
        'main.edit_user_permissions',
        {'user_id': 0},
        True,
        True,
    ),
    (
        'main.edit_user_permissions',
        {'user_id': 0},
        False,
        False,
    ),
    (
        'main.invite_user',
        {},
        True,
        True,
    ),
    (
        'main.invite_user',
        {},
        False,
        False,
    )
])
def test_service_without_caseworking_doesnt_show_admin_vs_caseworker(
    client_request,
    endpoint,
    extra_args,
    service_has_caseworking,
    radio_buttons_on_page,
    service_one
):
    if service_has_caseworking:
        service_one['permissions'].append('caseworking')
    page = client_request.get(endpoint, service_id=service_one['id'], **extra_args)
    radio_buttons = page.select('input[name=user_type]')
    admin_permissions_panel = page.select_one('#panel-admin')
    if radio_buttons_on_page:
        assert radio_buttons[0]['type'] == 'radio'
        assert radio_buttons[0]['value'] == 'caseworker'
        assert radio_buttons[1]['type'] == 'radio'
        assert radio_buttons[1]['value'] == 'admin'
        assert admin_permissions_panel.select('input')[0]['name'] == 'send_messages'
        assert admin_permissions_panel.select('input')[1]['name'] == 'manage_templates'
        assert admin_permissions_panel.select('input')[2]['name'] == 'manage_service'
        assert admin_permissions_panel.select('input')[3]['name'] == 'manage_api_keys'
    else:
        assert not radio_buttons
        assert not admin_permissions_panel


@pytest.mark.parametrize('service_has_email_auth, displays_auth_type', [
    (True, True),
    (False, False)
])
def test_manage_users_page_shows_member_auth_type_if_service_has_email_auth_activated(
    client_request,
    service_has_email_auth,
    service_one,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    displays_auth_type
):
    if service_has_email_auth:
        service_one['permissions'].append('email_auth')
    page = client_request.get('main.manage_users', service_id=service_one['id'])
    assert bool(page.select_one('.tick-cross-list-hint')) == displays_auth_type


@pytest.mark.parametrize('user, sms_option_disabled, expected_label', [
    (
        active_user_no_mobile,
        True,
        """
            Text message code
            Not available because this team member hasn’t added a
            phone number to their profile
        """,
    ),
    (
        active_user_with_permissions,
        False,
        """
            Text message code
        """,
    ),
])
def test_user_with_no_mobile_number_cant_be_set_to_sms_auth(
    client_request,
    user,
    sms_option_disabled,
    expected_label,
    service_one,
    mocker
):
    service_one['permissions'].append('email_auth')
    test_user = mocker.patch('app.user_api_client.get_user', return_value=user(mocker))

    page = client_request.get(
        'main.edit_user_permissions',
        service_id=service_one['id'],
        user_id=test_user.id
    )

    sms_auth_radio_button = page.select_one('input[value="sms_auth"]')
    assert sms_auth_radio_button.has_attr("disabled") == sms_option_disabled
    assert normalize_spaces(
        page.select_one('label[for=login_authentication-0]').text
    ) == normalize_spaces(expected_label)


@pytest.mark.parametrize('endpoint, extra_args, expected_checkboxes', [
    (
        'main.edit_user_permissions',
        {'user_id': 0},
        [
            ('send_messages', True),
            ('manage_templates', True),
            ('manage_service', True),
            ('manage_api_keys', True),
        ]
    ),
    (
        'main.invite_user',
        {},
        [
            ('send_messages', False),
            ('manage_templates', False),
            ('manage_service', False),
            ('manage_api_keys', False),
        ]
    ),
])
def test_should_show_page_for_one_user(
    client_request,
    endpoint,
    extra_args,
    expected_checkboxes,
):
    page = client_request.get(endpoint, service_id=SERVICE_ONE_ID, **extra_args)
    checkboxes = page.select('input[type=checkbox]')

    assert len(checkboxes) == 4

    for index, expected in enumerate(expected_checkboxes):
        expected_input_name, expected_checked = expected
        assert checkboxes[index]['name'] == expected_input_name
        assert checkboxes[index].has_attr('checked') == expected_checked


def test_edit_user_permissions(
    logged_in_client,
    active_user_with_permissions,
    mocker,
    mock_get_invites_for_service,
    mock_set_user_permissions,
):
    service = create_sample_service(active_user_with_permissions)
    response = logged_in_client.post(url_for(
        'main.edit_user_permissions', service_id=service['id'], user_id=active_user_with_permissions.id
    ), data={'email_address': active_user_with_permissions.email_address,
             'send_messages': 'y',
             'manage_templates': 'y',
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
            'send_messages',
            'manage_service',
            'manage_templates',
            'manage_api_keys',
            'view_activity'
        }
    )


def test_edit_some_user_permissions(
    logged_in_client,
    mocker,
    active_user_with_permissions,
    sample_invite,
    mock_get_invites_for_service,
    mock_set_user_permissions,
):
    service = create_sample_service(active_user_with_permissions)
    data = [InvitedUser(**sample_invite)]

    service_id = service['id']

    mocker.patch('app.invite_api_client.get_invites_for_service', return_value=data)
    response = logged_in_client.post(url_for(
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
            'send_messages',
            'view_activity'
        }
    )


@pytest.mark.parametrize('auth_type', ['email_auth', 'sms_auth'])
def test_edit_user_permissions_including_authentication_with_email_auth_service(
    logged_in_client,
    active_user_with_permissions,
    mocker,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    mock_update_user_attribute,
    service_one,
    auth_type
):
    service_one['permissions'].append('email_auth')

    response = logged_in_client.post(
        url_for(
            'main.edit_user_permissions',
            service_id=service_one['id'],
            user_id=active_user_with_permissions.id
        ),
        data={
            'email_address': active_user_with_permissions.email_address,
            'send_messages': 'y',
            'manage_templates': 'y',
            'manage_service': 'y',
            'manage_api_keys': 'y',
            'login_authentication': auth_type
        }
    )

    mock_set_user_permissions.assert_called_with(
        str(active_user_with_permissions.id),
        service_one['id'],
        permissions={
            'send_messages',
            'manage_templates',
            'manage_service',
            'manage_api_keys',
            'view_activity'
        }
    )
    mock_update_user_attribute.assert_called_with(
        str(active_user_with_permissions.id),
        auth_type=auth_type
    )

    assert response.status_code == 302
    assert response.location == url_for(
        'main.manage_users', service_id=service_one['id'], _external=True
    )


def test_edit_user_to_be_admin(
    client_request,
    active_user_with_permissions,
    mocker,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    service_one,
):
    service_one['permissions'].append('caseworking')
    client_request.post(
        'main.edit_user_permissions',
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions.id,
        _data={
            'email_address': active_user_with_permissions.email_address,
            'user_type': 'admin',
            'send_messages': 'y',
            'manage_templates': 'y',
            'manage_service': 'y',
            'manage_api_keys': 'y',
        },
        _expected_redirect=url_for(
            'main.manage_users', service_id=SERVICE_ONE_ID, _external=True
        ),
    )
    mock_set_user_permissions.assert_called_with(
        str(active_user_with_permissions.id),
        SERVICE_ONE_ID,
        permissions={
            'send_messages',
            'manage_service',
            'manage_templates',
            'manage_api_keys',
            'view_activity'
        }
    )


@pytest.mark.parametrize('extra_args', (
    # The user shouldn’t be able to forge a request which makes a
    # caseworker without the ‘send’ permission…
    ({'send_messages': 'n'}),
    # …or with any additional permissions
    ({'manage_templates': 'y'}),
    ({'manage_service': 'y'}),
    ({'manage_api_keys': 'y'}),
))
def test_edit_user_to_be_caseworker(
    client_request,
    active_user_with_permissions,
    mocker,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    service_one,
    extra_args,
):
    service_one['permissions'].append('caseworking')
    client_request.post(
        'main.edit_user_permissions',
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions.id,
        _data=dict(
            email_address=active_user_with_permissions.email_address,
            user_type='caseworker',
            **extra_args
        ),
        _expected_redirect=url_for(
            'main.manage_users', service_id=SERVICE_ONE_ID, _external=True
        ),
    )
    mock_set_user_permissions.assert_called_with(
        str(active_user_with_permissions.id),
        SERVICE_ONE_ID,
        permissions={
            'send_messages',
        }
    )


def test_should_show_page_for_inviting_user(
    logged_in_client,
    active_user_with_permissions,
    mocker,
):
    service = create_sample_service(active_user_with_permissions)
    response = logged_in_client.get(url_for('main.invite_user', service_id=service['id']))

    assert 'Invite a team member' in response.get_data(as_text=True)
    assert response.status_code == 200


@pytest.mark.parametrize('email_address, gov_user', [
    ('test@example.gov.uk', True),
    ('test@nonwhitelist.com', False)
])
def test_invite_user(
    logged_in_client,
    active_user_with_permissions,
    mocker,
    sample_invite,
    email_address,
    gov_user,
):
    service = create_sample_service(active_user_with_permissions)
    sample_invite['email_address'] = 'test@example.gov.uk'

    data = [InvitedUser(**sample_invite)]
    assert is_gov_user(email_address) == gov_user
    mocker.patch('app.invite_api_client.get_invites_for_service', return_value=data)
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])
    mocker.patch('app.invite_api_client.create_invite', return_value=InvitedUser(**sample_invite))
    response = logged_in_client.post(
        url_for('main.invite_user', service_id=service['id']),
        data={'email_address': email_address,
              'send_messages': 'y',
              'manage_templates': 'y',
              'manage_service': 'y',
              'manage_api_keys': 'y'},
        follow_redirects=True
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string.strip() == 'Team members'
    flash_banner = page.find('div', class_='banner-default-with-tick').string.strip()
    assert flash_banner == 'Invite sent to test@example.gov.uk'

    expected_permissions = {'manage_api_keys', 'manage_service', 'manage_templates', 'send_messages', 'view_activity'}

    app.invite_api_client.create_invite.assert_called_once_with(sample_invite['from_user'],
                                                                sample_invite['service'],
                                                                email_address,
                                                                expected_permissions,
                                                                'sms_auth')


@pytest.mark.parametrize('auth_type', [
    ('sms_auth'),
    ('email_auth')
])
@pytest.mark.parametrize('email_address, gov_user', [
    ('test@example.gov.uk', True),
    ('test@nonwhitelist.com', False)
])
def test_invite_user_with_email_auth_service(
    logged_in_client,
    active_user_with_permissions,
    sample_invite,
    email_address,
    gov_user,
    mocker,
    service_one,
    auth_type
):
    service_one['permissions'].append('email_auth')
    sample_invite['email_address'] = 'test@example.gov.uk'

    data = [InvitedUser(**sample_invite)]
    assert is_gov_user(email_address) == gov_user
    mocker.patch('app.invite_api_client.get_invites_for_service', return_value=data)
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])
    mocker.patch('app.invite_api_client.create_invite', return_value=InvitedUser(**sample_invite))
    response = logged_in_client.post(
        url_for('main.invite_user', service_id=service_one['id']),
        data={'email_address': email_address,
              'send_messages': 'y',
              'manage_templates': 'y',
              'manage_service': 'y',
              'manage_api_keys': 'y',
              'login_authentication': auth_type},
        follow_redirects=True
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string.strip() == 'Team members'
    flash_banner = page.find('div', class_='banner-default-with-tick').string.strip()
    assert flash_banner == 'Invite sent to test@example.gov.uk'

    expected_permissions = {'manage_api_keys', 'manage_service', 'manage_templates', 'send_messages', 'view_activity'}

    app.invite_api_client.create_invite.assert_called_once_with(sample_invite['from_user'],
                                                                sample_invite['service'],
                                                                email_address,
                                                                expected_permissions,
                                                                auth_type)


@pytest.mark.parametrize('extra_args', (
    {},
    {
        'send_messages': 'y',
        'manage_templates': 'y',
        'manage_service': 'y',
        'manage_api_keys': 'y',
    },
))
def test_invite_user_must_choose_caseworker_or_admin(
    client_request,
    mock_set_user_permissions,
    service_one,
    fake_uuid,
    extra_args,
):
    service_one['permissions'].append('caseworking')
    page = client_request.post(
        'main.invite_user',
        service_id=service_one['id'],
        user_id=fake_uuid,
        _data={
            'email_address': 'test@example.com',
            **extra_args
        },
        _expected_status=200,
    )
    assert page.select_one('.error-message').text.strip() == (
        'Not a valid choice'
    )
    assert mock_set_user_permissions.called is False
    for form_input in page.select('form input'):
        assert 'checked' not in form_input


def test_cancel_invited_user_cancels_user_invitations(
    logged_in_client,
    active_user_with_permissions,
    mocker,
):
    mocker.patch('app.invite_api_client.cancel_invited_user')
    import uuid
    invited_user_id = uuid.uuid4()
    service = create_sample_service(active_user_with_permissions)
    response = logged_in_client.get(url_for('main.cancel_invited_user', service_id=service['id'],
                                    invited_user_id=invited_user_id))

    assert response.status_code == 302
    assert response.location == url_for('main.manage_users', service_id=service['id'], _external=True)


@pytest.mark.parametrize('invite_status, expected_text', [
    ('pending', (
        'invited_user@test.gov.uk (invited) '
        'Can Send messages '
        'Can’t Add and edit templates '
        'Can Manage service '
        'Can Access API keys '
        'Cancel invitation'
    )),
    ('cancelled', (
        'invited_user@test.gov.uk (cancelled invite) '
        # all permissions are greyed out
        'Can’t Send messages '
        'Can’t Add and edit templates '
        'Can’t Manage service '
        'Can’t Access API keys'
    )),
])
def test_manage_users_shows_invited_user(
    client_request,
    mocker,
    active_user_with_permissions,
    sample_invite,
    invite_status,
    expected_text,
):
    sample_invite['status'] = invite_status
    data = [InvitedUser(**sample_invite)]
    mocker.patch('app.invite_api_client.get_invites_for_service', return_value=data)
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])

    page = client_request.get('main.manage_users', service_id=SERVICE_ONE_ID)
    assert page.h1.string.strip() == 'Team members'
    assert normalize_spaces(page.select('.user-list-item')[0].text) == expected_text


def test_manage_users_does_not_show_accepted_invite(
    logged_in_client,
    mocker,
    active_user_with_permissions,
    sample_invite,
):
    import uuid
    invited_user_id = uuid.uuid4()
    sample_invite['id'] = invited_user_id
    sample_invite['status'] = 'accepted'
    data = [InvitedUser(**sample_invite)]
    service = create_sample_service(active_user_with_permissions)
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])
    mocker.patch('app.invite_api_client.get_invites_for_service', return_value=data)

    response = logged_in_client.get(url_for('main.manage_users', service_id=service['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string.strip() == 'Team members'
    user_lists = page.find_all('div', {'class': 'user-list'})
    assert len(user_lists) == 1
    assert not page.find(text='invited_user@test.gov.uk')


def test_user_cant_invite_themselves(
    logged_in_client,
    mocker,
    active_user_with_permissions,
    mock_create_invite,
):
    service = create_sample_service(active_user_with_permissions)
    response = logged_in_client.post(
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
    assert form_error == "You can’t send an invitation to yourself"
    assert not mock_create_invite.called


def test_no_permission_manage_users_page(
    client_request,
    service_one,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    api_user_active,
    mocker,
):
    resp_text = client_request.get('main.manage_users', service_id=service_one['id'])
    assert url_for('.invite_user', service_id=service_one['id']) not in resp_text
    assert "Edit permission" not in resp_text
    assert "Team members" not in resp_text


def test_get_remove_user_from_service(
    logged_in_client,
    active_user_with_permissions,
    service_one,
    mocker,
):
    response = logged_in_client.get(
        url_for(
            'main.remove_user_from_service',
            service_id=service_one['id'],
            user_id=active_user_with_permissions.id))
    assert response.status_code == 200
    assert "Are you sure you want to remove" in response.get_data(as_text=True)
    assert "Remove user from service" in response.get_data(as_text=True)


def test_remove_user_from_service(
    logged_in_client,
    active_user_with_permissions,
    service_one,
    mocker,
    mock_get_users_by_service,
    mock_get_user,
    mock_remove_user_from_service,
):
    response = logged_in_client.post(
        url_for(
            'main.remove_user_from_service',
            service_id=service_one['id'],
            user_id=active_user_with_permissions.id))
    assert response.status_code == 302
    assert response.location == url_for(
        'main.manage_users', service_id=service_one['id'], _external=True)
    mock_remove_user_from_service.assert_called_once_with(service_one['id'],
                                                          str(active_user_with_permissions.id))


def test_can_remove_user_from_service_as_platform_admin(
    logged_in_client,
    service_one,
    platform_admin_user,
    active_user_with_permissions,
    mock_remove_user_from_service,
    mocker,
):
    response = logged_in_client.post(
        url_for(
            'main.remove_user_from_service',
            service_id=service_one['id'],
            user_id=active_user_with_permissions.id))
    assert response.status_code == 302
    assert response.location == url_for(
        'main.manage_users', service_id=service_one['id'], _external=True)
    mock_remove_user_from_service.assert_called_once_with(service_one['id'],
                                                          str(active_user_with_permissions.id))


def test_can_invite_user_as_platform_admin(
    logged_in_client,
    service_one,
    platform_admin_user,
    active_user_with_permissions,
    mock_get_invites_for_service,
    mocker,
):
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])

    response = logged_in_client.get(url_for('main.manage_users', service_id=service_one['id']))
    resp_text = response.get_data(as_text=True)
    assert url_for('.invite_user', service_id=service_one['id']) in resp_text

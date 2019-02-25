import copy
import uuid

import pytest
from bs4 import BeautifulSoup
from flask import url_for

import app
from app.models.user import InvitedUser
from app.utils import is_gov_user
from tests.conftest import (
    SERVICE_ONE_ID,
    active_caseworking_user,
    active_user_empty_permissions,
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
            'Can See dashboard '
            'Can Send messages '
            'Can Add and edit templates '
            'Can Manage settings, team and usage '
            'Can Manage API integration'
        ),
        (
            'ZZZZZZZZ zzzzzzz@example.gov.uk '
            'Can See dashboard '
            'Can’t Send messages '
            'Can’t Add and edit templates '
            'Can’t Manage settings, team and usage '
            'Can’t Manage API integration '
            'Edit team member'
        )
    ),
    (
        active_user_empty_permissions,
        (
            'Test User With Empty Permissions (you) '
            'Can’t See dashboard '
            'Can’t Send messages '
            'Can’t Add and edit templates '
            'Can’t Manage settings, team and usage '
            'Can’t Manage API integration'
        ),
        (
            'ZZZZZZZZ zzzzzzz@example.gov.uk '
            'Can See dashboard '
            'Can’t Send messages '
            'Can’t Add and edit templates '
            'Can’t Manage settings, team and usage '
            'Can’t Manage API integration'
        ),
    ),
    (
        active_user_view_permissions,
        (
            'Test User With Permissions (you) '
            'Can See dashboard '
            'Can’t Send messages '
            'Can’t Add and edit templates '
            'Can’t Manage settings, team and usage '
            'Can’t Manage API integration'
        ),
        (
            'ZZZZZZZZ zzzzzzz@example.gov.uk '
            'Can See dashboard '
            'Can’t Send messages '
            'Can’t Add and edit templates '
            'Can’t Manage settings, team and usage '
            'Can’t Manage API integration'
        )
    ),
    (
        active_user_manage_template_permission,
        (
            'Test User With Permissions (you) '
            'Can See dashboard '
            'Can’t Send messages '
            'Can Add and edit templates '
            'Can’t Manage settings, team and usage '
            'Can’t Manage API integration'
        ),
        (
            'ZZZZZZZZ zzzzzzz@example.gov.uk '
            'Can See dashboard '
            'Can’t Send messages '
            'Can’t Add and edit templates '
            'Can’t Manage settings, team and usage '
            'Can’t Manage API integration'
        )
    ),
    (
        active_user_manage_template_permission,
        (
            'Test User With Permissions (you) '
            'Can See dashboard '
            'Can’t Send messages '
            'Can Add and edit templates '
            'Can’t Manage settings, team and usage '
            'Can’t Manage API integration'
        ),
        (
            'ZZZZZZZZ zzzzzzz@example.gov.uk '
            'Can See dashboard '
            'Can’t Send messages '
            'Can’t Add and edit templates '
            'Can’t Manage settings, team and usage '
            'Can’t Manage API integration'
        )
    ),
])
def test_should_show_overview_page(
    client_request,
    mocker,
    mock_get_invites_for_service,
    mock_has_no_jobs,
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
        'Can See dashboard '
        'Can’t Send messages '
        'Can’t Add and edit templates '
        'Can’t Manage settings, team and usage '
        'Can’t Manage API integration'
    )
    # [1:5] are invited users
    assert normalize_spaces(page.select('.user-list-item')[6].text) == (
        'Test User zzzzzzz@example.gov.uk '
        'Can’t See dashboard '
        'Can Send messages '
        'Can’t Add and edit templates '
        'Can’t Manage settings, team and usage '
        'Can’t Manage API integration'
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


@pytest.mark.parametrize('service_has_caseworking', (True, False))
@pytest.mark.parametrize('endpoint, extra_args', [
    (
        'main.edit_user_permissions',
        {'user_id': 0},
    ),
    (
        'main.invite_user',
        {},
    ),
])
def test_service_without_caseworking_doesnt_show_admin_vs_caseworker(
    client_request,
    endpoint,
    service_has_caseworking,
    extra_args,
):
    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        **extra_args
    )
    assert page.select('input[type=checkbox]')[0]['name'] == 'view_activity'
    assert page.select('input[type=checkbox]')[1]['name'] == 'send_messages'
    assert page.select('input[type=checkbox]')[2]['name'] == 'manage_templates'
    assert page.select('input[type=checkbox]')[3]['name'] == 'manage_service'
    assert page.select('input[type=checkbox]')[4]['name'] == 'manage_api_keys'


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
            ('view_activity', True),
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
            ('view_activity', False),
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

    assert len(checkboxes) == 5

    for index, expected in enumerate(expected_checkboxes):
        expected_input_name, expected_checked = expected
        assert checkboxes[index]['name'] == expected_input_name
        assert checkboxes[index].has_attr('checked') == expected_checked


@pytest.mark.parametrize('submitted_permissions, permissions_sent_to_api', [
    (
        {
            'view_activity': 'y',
            'send_messages': 'y',
            'manage_templates': 'y',
            'manage_service': 'y',
            'manage_api_keys': 'y',
        },
        {
            'view_activity',
            'send_messages',
            'manage_service',
            'manage_templates',
            'manage_api_keys',
        }
    ),
    (
        {
            'view_activity': 'y',
            'send_messages': 'y',
            'manage_templates': '',
        },
        {
            'view_activity',
            'send_messages',
        }
    ),
    (
        {},
        set(),
    ),
])
def test_edit_user_permissions(
    client_request,
    mocker,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    fake_uuid,
    submitted_permissions,
    permissions_sent_to_api,
):
    client_request.post(
        'main.edit_user_permissions',
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
        _data=dict(
            email_address="test@example.com",
            **submitted_permissions
        ),
        _expected_status=302,
        _expected_redirect=url_for(
            'main.manage_users',
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    )
    mock_set_user_permissions.assert_called_with(
        fake_uuid,
        SERVICE_ONE_ID,
        permissions=permissions_sent_to_api,
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
              'view_activity': 'y',
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
              'view_activity': 'y',
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
        'Can See dashboard '
        'Can Send messages '
        'Can’t Add and edit templates '
        'Can Manage settings, team and usage '
        'Can Manage API integration '
        'Cancel invitation'
    )),
    ('cancelled', (
        'invited_user@test.gov.uk (cancelled invite) '
        # all permissions are greyed out
        'Can’t See dashboard '
        'Can’t Send messages '
        'Can’t Add and edit templates '
        'Can’t Manage settings, team and usage '
        'Can’t Manage API integration'
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
    client_request,
    mocker,
    active_user_with_permissions,
    sample_invite,
):
    invited_user_id = uuid.uuid4()
    sample_invite['id'] = invited_user_id
    sample_invite['status'] = 'accepted'
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])
    mocker.patch('app.invite_api_client._get_invites_for_service', return_value=[sample_invite])

    page = client_request.get('main.manage_users', service_id=SERVICE_ONE_ID)

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


def test_edit_user_email_page(
    client_request,
    active_user_with_permissions,
    service_one,
    mocker
):
    user = active_user_with_permissions
    test_user = mocker.patch('app.user_api_client.get_user', return_value=user)

    page = client_request.get(
        'main.edit_user_email',
        service_id=service_one['id'],
        user_id=test_user.id
    )

    assert page.find('h1').text == "Change team member’s email address"
    assert page.select('p[id=user_name]')[0].text == "This will change the email address for {}.".format(user.name)
    assert page.select('input[type=email]')[0].attrs["value"] == user.email_address
    assert page.select('button[type=submit]')[0].text == "Save"


def test_edit_user_email_redirects_to_confirmation(
    logged_in_client,
    active_user_with_permissions,
    service_one,
    mocker,
    mock_get_user,
):
    response = logged_in_client.post(
        url_for(
            'main.edit_user_email',
            service_id=service_one['id'],
            user_id=active_user_with_permissions.id))
    assert response.status_code == 302
    assert response.location == url_for(
        'main.confirm_edit_user_email',
        service_id=service_one['id'],
        user_id=active_user_with_permissions.id,
        _external=True
    )


def test_edit_user_email_without_changing_goes_back_to_team_members(
    client_request,
    active_user_with_permissions,
    mock_get_user,
    mock_update_user_attribute,
):
    client_request.post(
        'main.edit_user_email',
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions.id,
        _data={
            'email_address': active_user_with_permissions.email_address
        },
        _expected_status=302,
        _expected_redirect=url_for(
            'main.manage_users',
            service_id=SERVICE_ONE_ID,
            _external=True
        ),
    )
    assert mock_update_user_attribute.called is False


def test_confirm_edit_user_email_page(
    logged_in_client,
    active_user_with_permissions,
    service_one,
    mocker,
    mock_get_user,
):
    new_email = 'new_email@gov.uk'
    with logged_in_client.session_transaction() as session:
        session['team_member_email_change'] = new_email
    response = logged_in_client.get(url_for(
        'main.confirm_edit_user_email',
        service_id=service_one['id'],
        user_id=active_user_with_permissions.id
    ))

    assert 'Confirm change of email address' in response.get_data(as_text=True)
    for text in [
        'New email address:',
        new_email,
        'We will send {} an email to tell them about the change.'.format(active_user_with_permissions.name)
    ]:
        assert text in response.get_data(as_text=True)
    assert 'Confirm' in response.get_data(as_text=True)
    assert response.status_code == 200


def test_confirm_edit_user_email_page_redirects_if_session_empty(
    logged_in_client,
    active_user_with_permissions,
    service_one,
    mocker,
    mock_get_user,
):
    response = logged_in_client.get(url_for(
        'main.confirm_edit_user_email',
        service_id=service_one['id'],
        user_id=active_user_with_permissions.id
    ))
    assert response.status_code == 302
    assert 'Confirm change of email address' not in response.get_data(as_text=True)


def test_confirm_edit_user_email_changes_user_email(
    logged_in_client,
    active_user_with_permissions,
    service_one,
    mocker,
    mock_get_user,
    mock_update_user_attribute
):
    new_email = 'new_email@gov.uk'
    with logged_in_client.session_transaction() as session:
        session['team_member_email_change'] = new_email
    response = logged_in_client.post(
        url_for(
            'main.confirm_edit_user_email',
            service_id=service_one['id'],
            user_id=active_user_with_permissions.id))
    assert response.status_code == 302
    assert response.location == url_for(
        'main.manage_users', service_id=service_one['id'], _external=True)
    mock_update_user_attribute.assert_called_once_with(active_user_with_permissions.id, email_address=new_email)

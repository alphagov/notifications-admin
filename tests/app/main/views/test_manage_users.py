import copy
import uuid

import pytest
from flask import url_for

import app
from app.models.user import InvitedUser
from app.utils import is_gov_user
from tests.conftest import (
    SERVICE_ONE_ID,
    USER_ONE_ID,
    active_caseworking_user,
    active_user_empty_permissions,
    active_user_manage_template_permission,
    active_user_no_mobile,
    active_user_view_permissions,
    active_user_with_permissions,
    normalize_spaces,
    sample_uuid,
)


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
        {'user_id': sample_uuid()},
        True,
        False
    ),
    (
        'main.edit_user_permissions',
        {'user_id': sample_uuid()},
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
    service_one,
    mock_get_users_by_service,
    mock_get_template_folders
):
    if service_has_email_auth:
        service_one['permissions'].append('email_auth')
    page = client_request.get(endpoint, service_id=service_one['id'], **extra_args)
    assert (page.find('input', attrs={"name": "login_authentication"}) is None) == auth_options_hidden


@pytest.mark.parametrize('service_has_caseworking', (True, False))
@pytest.mark.parametrize('endpoint, extra_args', [
    (
        'main.edit_user_permissions',
        {'user_id': sample_uuid()},
    ),
    (
        'main.invite_user',
        {},
    ),
])
def test_service_without_caseworking_doesnt_show_admin_vs_caseworker(
    client_request,
    mock_get_users_by_service,
    mock_get_template_folders,
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
    mock_get_users_by_service,
    mock_get_template_folders,
    user,
    sms_option_disabled,
    expected_label,
    service_one,
    mocker
):
    service_one['permissions'].append('email_auth')
    mocker.patch('app.user_api_client.get_user', return_value=user(mocker))

    page = client_request.get(
        'main.edit_user_permissions',
        service_id=service_one['id'],
        user_id=sample_uuid(),
    )

    sms_auth_radio_button = page.select_one('input[value="sms_auth"]')
    assert sms_auth_radio_button.has_attr("disabled") == sms_option_disabled
    assert normalize_spaces(
        page.select_one('label[for=login_authentication-0]').text
    ) == normalize_spaces(expected_label)


@pytest.mark.parametrize('endpoint, extra_args, expected_checkboxes', [
    (
        'main.edit_user_permissions',
        {'user_id': sample_uuid()},
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
    mock_get_users_by_service,
    mock_get_template_folders,
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


def test_invite_user_allows_to_choose_auth(
    client_request,
    mock_get_users_by_service,
    mock_get_template_folders,
    service_one,
):
    service_one['permissions'].append('email_auth')
    page = client_request.get('main.invite_user', service_id=SERVICE_ONE_ID)

    sms_auth_radio_button = page.select_one('input[value="sms_auth"]')
    assert sms_auth_radio_button.has_attr("disabled") is False


def test_should_not_show_page_for_non_team_member(
    client_request,
    mock_get_users_by_service,
):
    client_request.get(
        'main.edit_user_permissions',
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _expected_status=404,
    )


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
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    mock_get_template_folders,
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
        folder_permissions=None
    )


def test_edit_user_folder_permissions(
    client_request,
    mocker,
    service_one,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    mock_get_template_folders,
    fake_uuid,
):
    service_one['permissions'] = ['edit_folder_permissions']
    mock_get_template_folders.return_value = [
        {'id': 'folder-id-1', 'name': 'folder_one', 'parent_id': None, 'users_with_permission': []},
        {'id': 'folder-id-2', 'name': 'folder_one', 'parent_id': None, 'users_with_permission': []},
        {'id': 'folder-id-3', 'name': 'folder_one', 'parent_id': 'folder-id-1', 'users_with_permission': []},
    ]
    client_request.post(
        'main.edit_user_permissions',
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
        _data=dict(
            folder_permissions=['folder-id-1', 'folder-id-3']
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
        permissions=set(),
        folder_permissions=['folder-id-1', 'folder-id-3']
    )


def test_cant_edit_non_member_user_permissions(
    client_request,
    mocker,
    mock_get_users_by_service,
    mock_set_user_permissions,
):
    client_request.post(
        'main.edit_user_permissions',
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _data={
            'email_address': 'test@example.com',
            'manage_service': 'y',
        },
        _expected_status=404,
    )
    assert mock_set_user_permissions.called is False


@pytest.mark.parametrize('auth_type', ['email_auth', 'sms_auth'])
def test_edit_user_permissions_including_authentication_with_email_auth_service(
    client_request,
    service_one,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    mock_update_user_attribute,
    auth_type,
    mock_get_template_folders
):
    service_one['permissions'].append('email_auth')

    client_request.post(
        'main.edit_user_permissions',
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions.id,
        _data={
            'email_address': active_user_with_permissions.email_address,
            'send_messages': 'y',
            'manage_templates': 'y',
            'manage_service': 'y',
            'manage_api_keys': 'y',
            'login_authentication': auth_type,
        },
        _expected_status=302,
        _expected_redirect=url_for(
            'main.manage_users',
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    )

    mock_set_user_permissions.assert_called_with(
        str(active_user_with_permissions.id),
        SERVICE_ONE_ID,
        permissions={
            'send_messages',
            'manage_templates',
            'manage_service',
            'manage_api_keys',
        },
        folder_permissions=None
    )
    mock_update_user_attribute.assert_called_with(
        str(active_user_with_permissions.id),
        auth_type=auth_type
    )


def test_should_show_page_for_inviting_user(
    client_request,
    mock_get_template_folders,
):
    page = client_request.get(
        'main.invite_user',
        service_id=SERVICE_ONE_ID,
    )

    assert 'Invite a team member' in page.find('h1').text.strip()
    assert not page.find('div', class_='checkboxes-nested')


def test_should_show_folder_permission_form_if_service_has_folder_permissions_enabled(
    client_request,
    mocker,
    mock_get_template_folders,
    service_one
):
    service_one['permissions'].append('edit_folder_permissions')
    mock_get_template_folders.return_value = [
        {'id': 'folder-id-1', 'name': 'folder_one', 'parent_id': None, 'users_with_permission': []},
        {'id': 'folder-id-2', 'name': 'folder_two', 'parent_id': None, 'users_with_permission': []},
        {'id': 'folder-id-3', 'name': 'folder_three', 'parent_id': 'folder-id-1', 'users_with_permission': []},
    ]
    page = client_request.get(
        'main.invite_user',
        service_id=SERVICE_ONE_ID,
    )

    assert 'Invite a team member' in page.find('h1').text.strip()

    folder_checkboxes = page.find('div', class_='checkboxes-nested').find_all('li')
    assert len(folder_checkboxes) == 3


@pytest.mark.parametrize('email_address, gov_user', [
    ('test@example.gov.uk', True),
    ('test@nonwhitelist.com', False)
])
def test_invite_user(
    client_request,
    active_user_with_permissions,
    mocker,
    sample_invite,
    email_address,
    gov_user,
    mock_get_template_folders,
):
    sample_invite['email_address'] = 'test@example.gov.uk'

    data = [InvitedUser(**sample_invite)]
    assert is_gov_user(email_address) == gov_user
    mocker.patch('app.invite_api_client.get_invites_for_service', return_value=data)
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])
    mocker.patch('app.invite_api_client.create_invite', return_value=InvitedUser(**sample_invite))
    page = client_request.post(
        'main.invite_user',
        service_id=SERVICE_ONE_ID,
        _data={
            'email_address': email_address,
            'view_activity': 'y',
            'send_messages': 'y',
            'manage_templates': 'y',
            'manage_service': 'y',
            'manage_api_keys': 'y',
        },
        _follow_redirects=True,
    )
    assert page.h1.string.strip() == 'Team members'
    flash_banner = page.find('div', class_='banner-default-with-tick').string.strip()
    assert flash_banner == 'Invite sent to test@example.gov.uk'

    expected_permissions = {'manage_api_keys', 'manage_service', 'manage_templates', 'send_messages', 'view_activity'}

    app.invite_api_client.create_invite.assert_called_once_with(sample_invite['from_user'],
                                                                sample_invite['service'],
                                                                email_address,
                                                                expected_permissions,
                                                                'sms_auth',
                                                                [])


@pytest.mark.parametrize('auth_type', [
    ('sms_auth'),
    ('email_auth')
])
@pytest.mark.parametrize('email_address, gov_user', [
    ('test@example.gov.uk', True),
    ('test@nonwhitelist.com', False)
])
def test_invite_user_with_email_auth_service(
    client_request,
    service_one,
    active_user_with_permissions,
    sample_invite,
    email_address,
    gov_user,
    mocker,
    auth_type,
    mock_get_template_folders,
):
    service_one['permissions'].append('email_auth')
    sample_invite['email_address'] = 'test@example.gov.uk'

    data = [InvitedUser(**sample_invite)]
    assert is_gov_user(email_address) == gov_user
    mocker.patch('app.invite_api_client.get_invites_for_service', return_value=data)
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])
    mocker.patch('app.invite_api_client.create_invite', return_value=InvitedUser(**sample_invite))
    page = client_request.post(
        'main.invite_user',
        service_id=SERVICE_ONE_ID,
        _data={
            'email_address': email_address,
            'view_activity': 'y',
            'send_messages': 'y',
            'manage_templates': 'y',
            'manage_service': 'y',
            'manage_api_keys': 'y',
            'login_authentication': auth_type,
        },
        _follow_redirects=True,
        _expected_status=200,
    )

    assert page.h1.string.strip() == 'Team members'
    flash_banner = page.find('div', class_='banner-default-with-tick').string.strip()
    assert flash_banner == 'Invite sent to test@example.gov.uk'

    expected_permissions = {'manage_api_keys', 'manage_service', 'manage_templates', 'send_messages', 'view_activity'}

    app.invite_api_client.create_invite.assert_called_once_with(sample_invite['from_user'],
                                                                sample_invite['service'],
                                                                email_address,
                                                                expected_permissions,
                                                                auth_type,
                                                                [])


def test_invite_user_sends_invite_with_all_folders_if_folder_permissions_not_enabled(
    client_request,
    mocker,
    mock_get_template_folders,
    service_one
):
    mocker.patch('app.invite_api_client.get_invites_for_service')
    mocker.patch('app.user_api_client.get_users_for_service')
    mock_get_template_folders.return_value = [
        {'id': 'folder-id-1', 'name': 'folder_one', 'parent_id': None, 'users_with_permission': []},
        {'id': 'folder-id-2', 'name': 'folder_two', 'parent_id': None, 'users_with_permission': []},
        {'id': 'folder-id-3', 'name': 'folder_three', 'parent_id': 'folder-id-1', 'users_with_permission': []},
    ]
    invite_mock = mocker.patch('app.invite_api_client.create_invite')

    client_request.post(
        'main.invite_user',
        service_id=SERVICE_ONE_ID,
        _data={
            'email_address': 'user@example.com',
            'send_messages': 'y',
        },
        _follow_redirects=True,
        _expected_status=200,
    )

    folder_data_sent = invite_mock.call_args[0][-1]

    assert len(folder_data_sent) == 3
    assert 'folder-id-1' in folder_data_sent
    assert 'folder-id-2' in folder_data_sent
    assert 'folder-id-3' in folder_data_sent


def test_cancel_invited_user_cancels_user_invitations(
    client_request,
    mock_get_invites_for_service,
    active_user_with_permissions,
    mocker,
):
    mock_cancel = mocker.patch('app.invite_api_client.cancel_invited_user')
    client_request.get(
        'main.cancel_invited_user',
        service_id=SERVICE_ONE_ID,
        invited_user_id=sample_uuid(),
        _expected_status=302,
        _expected_redirect=url_for(
            'main.manage_users', service_id=SERVICE_ONE_ID, _external=True
        ),
    )
    mock_cancel.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        invited_user_id=sample_uuid(),
    )


def test_cancel_invited_user_doesnt_work_if_user_not_invited_to_this_service(
    client_request,
    mock_get_invites_for_service,
    mocker,
):
    mock_cancel = mocker.patch('app.invite_api_client.cancel_invited_user')
    client_request.get(
        'main.cancel_invited_user',
        service_id=SERVICE_ONE_ID,
        invited_user_id=USER_ONE_ID,
        _expected_status=404,
    )
    assert mock_cancel.called is False


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
    client_request,
    mocker,
    active_user_with_permissions,
    mock_create_invite,
    mock_get_template_folders,
):
    page = client_request.post(
        'main.invite_user',
        service_id=SERVICE_ONE_ID,
        _data={
            'email_address': active_user_with_permissions.email_address,
            'send_messages': 'y',
            'manage_service': 'y',
            'manage_api_keys': 'y',
        },
        _follow_redirects=True,
        _expected_status=200,
    )
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


def test_remove_user_from_service(
    client_request,
    active_user_with_permissions,
    service_one,
    mock_remove_user_from_service,
):
    client_request.post(
        'main.remove_user_from_service',
        service_id=service_one['id'],
        user_id=active_user_with_permissions.id,
        _expected_redirect=url_for('main.manage_users', service_id=service_one['id'], _external=True)
    )
    mock_remove_user_from_service.assert_called_once_with(
        service_one['id'],
        str(active_user_with_permissions.id)
    )


def test_can_invite_user_as_platform_admin(
    client_request,
    service_one,
    platform_admin_user,
    active_user_with_permissions,
    mock_get_invites_for_service,
    mocker,
):
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[active_user_with_permissions])

    page = client_request.get(
        'main.manage_users',
        service_id=SERVICE_ONE_ID,
    )
    assert url_for('.invite_user', service_id=service_one['id']) in str(page)


def test_edit_user_email_page(
    client_request,
    active_user_with_permissions,
    service_one,
    mock_get_users_by_service,
    mocker
):
    user = active_user_with_permissions
    mocker.patch('app.user_api_client.get_user', return_value=user)

    page = client_request.get(
        'main.edit_user_email',
        service_id=service_one['id'],
        user_id=sample_uuid()
    )

    assert page.find('h1').text == "Change team member’s email address"
    assert page.select('p[id=user_name]')[0].text == "This will change the email address for {}.".format(user.name)
    assert page.select('input[type=email]')[0].attrs["value"] == user.email_address
    assert page.select('button[type=submit]')[0].text == "Save"


def test_edit_user_email_page_404_for_non_team_member(
    client_request,
    mock_get_users_by_service,
):
    client_request.get(
        'main.edit_user_email',
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _expected_status=404,
    )


def test_edit_user_email_redirects_to_confirmation(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
):
    client_request.post(
        'main.edit_user_email',
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions.id,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.confirm_edit_user_email',
            service_id=SERVICE_ONE_ID,
            user_id=active_user_with_permissions.id,
            _external=True,
        ),
    )


def test_edit_user_email_without_changing_goes_back_to_team_members(
    client_request,
    active_user_with_permissions,
    mock_get_user,
    mock_get_users_by_service,
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
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_get_user,
):
    new_email = 'new_email@gov.uk'
    with client_request.session_transaction() as session:
        session['team_member_email_change'] = new_email

    page = client_request.get(
        'main.confirm_edit_user_email',
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions.id,
    )

    assert 'Confirm change of email address' in page.text
    for text in [
        'New email address:',
        new_email,
        'We will send {} an email to tell them about the change.'.format(active_user_with_permissions.name)
    ]:
        assert text in page.text
    assert 'Confirm' in page.text


def test_confirm_edit_user_email_page_redirects_if_session_empty(
    client_request,
    mock_get_users_by_service,
    active_user_with_permissions,
):
    page = client_request.get(
        'main.confirm_edit_user_email',
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions.id,
        _follow_redirects=True,
    )
    assert 'Confirm change of email address' not in page.text


def test_confirm_edit_user_email_page_404s_for_non_team_member(
    client_request,
    mock_get_users_by_service,
):
    client_request.get(
        'main.confirm_edit_user_email',
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _expected_status=404,
    )


def test_confirm_edit_user_email_changes_user_email(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    service_one,
    mocker,
    mock_get_user,
    mock_update_user_attribute
):
    new_email = 'new_email@gov.uk'
    with client_request.session_transaction() as session:
        session['team_member_email_change'] = new_email
    client_request.post(
        'main.confirm_edit_user_email',
        service_id=service_one['id'],
        user_id=active_user_with_permissions.id,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.manage_users',
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    )
    mock_update_user_attribute.assert_called_once_with(
        active_user_with_permissions.id,
        email_address=new_email,
        updated_by=mocker.ANY
    )


def test_confirm_edit_user_email_doesnt_change_user_email_for_non_team_member(
    client_request,
    mock_get_users_by_service,
):
    with client_request.session_transaction() as session:
        session['team_member_email_change'] = 'new_email@gov.uk'
    client_request.post(
        'main.confirm_edit_user_email',
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _expected_status=404,
    )


def test_edit_user_permissions_page_displays_redacted_mobile_number_and_change_link(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_get_template_folders,
    service_one,
    mocker
):
    user = active_user_with_permissions
    mocker.patch('app.user_api_client.get_user', return_value=user)

    page = client_request.get(
        'main.edit_user_permissions',
        service_id=service_one['id'],
        user_id=user.id
    )

    assert user.name in page.find('h1').text
    mobile_number_paragraph = page.select('p[id=user_mobile_number]')[0]
    assert '0770 •  •  •  • 762' in mobile_number_paragraph.text
    change_link = mobile_number_paragraph.findChild()
    assert change_link.attrs['href'] == '/services/{}/users/{}/edit-mobile-number'.format(
        service_one['id'], user.id
    )


def test_edit_user_permissions_with_delete_query_shows_banner(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_get_template_folders,
    service_one
):
    page = client_request.get(
        'main.edit_user_permissions',
        service_id=service_one['id'],
        user_id=active_user_with_permissions.id,
        delete=1
    )

    banner = page.find('div', class_='banner-dangerous')
    assert banner.contents[0].strip() == "Are you sure you want to remove Test User?"
    assert banner.form.attrs['action'] == url_for(
        'main.remove_user_from_service',
        service_id=service_one['id'],
        user_id=active_user_with_permissions.id
    )


def test_edit_user_mobile_number_page(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    service_one,
    mocker
):
    user = active_user_with_permissions
    mocker.patch('app.user_api_client.get_user', return_value=user)

    page = client_request.get(
        'main.edit_user_mobile_number',
        service_id=service_one['id'],
        user_id=user.id
    )

    assert page.find('h1').text == "Change team member’s mobile number"
    assert page.select('p[id=user_name]')[0].text == "This will change the mobile number for {}.".format(user.name)
    assert page.select('input[name=mobile_number]')[0].attrs["value"] == "0770••••762"
    assert page.select('button[type=submit]')[0].text == "Save"


def test_edit_user_mobile_number_redirects_to_confirmation(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
):
    client_request.post(
        'main.edit_user_mobile_number',
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions.id,
        _data={'mobile_number': '07554080636'},
        _expected_status=302,
        _expected_redirect=url_for(
            'main.confirm_edit_user_mobile_number',
            service_id=SERVICE_ONE_ID,
            user_id=active_user_with_permissions.id,
            _external=True,
        ),
    )


def test_edit_user_mobile_number_redirects_to_manage_users_if_number_not_changed(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    service_one,
    mocker,
    mock_get_user,
):
    client_request.post(
        'main.edit_user_mobile_number',
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions.id,
        _data={'mobile_number': '0770••••762'},
        _expected_status=302,
        _expected_redirect=url_for(
            'main.manage_users',
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    )


def test_confirm_edit_user_mobile_number_page(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    service_one,
    mocker,
    mock_get_user,
):
    new_number = '07554080636'
    with client_request.session_transaction() as session:
        session['team_member_mobile_change'] = new_number
    page = client_request.get(
        'main.confirm_edit_user_mobile_number',
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions.id,
    )

    assert 'Confirm change of mobile number' in page.text
    for text in [
        'New mobile number:',
        new_number,
        'We will send {} a text message to tell them about the change.'.format(active_user_with_permissions.name)
    ]:
        assert text in page.text
    assert 'Confirm' in page.text


def test_confirm_edit_user_mobile_number_page_redirects_if_session_empty(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    service_one,
    mocker,
    mock_get_user,
):
    page = client_request.get(
        'main.confirm_edit_user_mobile_number',
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions.id,
        _expected_status=302,
    )
    assert 'Confirm change of mobile number' not in page.text


def test_confirm_edit_user_mobile_number_changes_user_mobile_number(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    service_one,
    mocker,
    mock_get_user,
    mock_update_user_attribute
):
    new_number = '07554080636'
    with client_request.session_transaction() as session:
        session['team_member_mobile_change'] = new_number
    client_request.post(
        'main.confirm_edit_user_mobile_number',
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions.id,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.manage_users',
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    )
    mock_update_user_attribute.assert_called_once_with(
        active_user_with_permissions.id,
        mobile_number=new_number,
        updated_by=mocker.ANY
    )


def test_confirm_edit_user_mobile_number_doesnt_change_user_mobile_for_non_team_member(
    client_request,
    mock_get_users_by_service,
):
    with client_request.session_transaction() as session:
        session['team_member_mobile_change'] = '07554080636'
    client_request.post(
        'main.confirm_edit_user_mobile_number',
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _expected_status=404,
    )

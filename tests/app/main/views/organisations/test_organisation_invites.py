from datetime import datetime, timedelta
from unittest.mock import ANY, Mock

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from notifications_python_client.errors import HTTPError

from app.models.user import InvitedOrgUser
from tests import organisation_json
from tests.conftest import (
    ORGANISATION_ID,
    active_user_with_permissions,
    normalize_spaces,
    platform_admin_user,
)


def test_organisation_page_shows_all_organisations(
    logged_in_platform_admin_client,
    mocker
):
    orgs = [
        {'id': '1', 'name': 'Test 1', 'active': True},
        {'id': '2', 'name': 'Test 2', 'active': True},
        {'id': '3', 'name': 'Test 3', 'active': False},
    ]

    mocker.patch(
        'app.organisations_client.get_organisations', return_value=orgs
    )
    response = logged_in_platform_admin_client.get(
        url_for('.organisations')
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(
        page.select_one('h1').text
    ) == "Organisations"

    for index, org in enumerate(orgs):
        assert page.select('a.browse-list-link')[index].text == org['name']
        if not org['active']:
            assert page.select_one('.table-field-status-default,heading-medium').text == '- archived'
    assert normalize_spaces(
        page.select_one('a.button-secondary').text
    ) == 'New organisation'


def test_view_organisation_shows_the_correct_organisation(
    client_request,
    mocker
):
    org = {'id': ORGANISATION_ID, 'name': 'Test 1', 'active': True}
    mocker.patch(
        'app.organisations_client.get_organisation', return_value=org
    )
    mocker.patch(
        'app.organisations_client.get_organisation_services', return_value=[]
    )

    page = client_request.get(
        '.organisation_dashboard',
        org_id=ORGANISATION_ID,
    )

    assert normalize_spaces(page.select_one('h1').text) == 'Services'


def test_create_new_organisation(
    logged_in_platform_admin_client,
    mocker,
    fake_uuid
):
    mock_create_organisation = mocker.patch(
        'app.organisations_client.create_organisation'
    )

    org = {'name': 'new name'}

    logged_in_platform_admin_client.post(
        url_for('.add_organisation'),
        content_type='multipart/form-data',
        data=org
    )

    mock_create_organisation.assert_called_once_with(name=org['name'])


def test_organisation_services_show(
    client_request,
    mock_get_organisation,
    mock_get_organisation_services,
    mocker,
    fake_uuid,
):
    page = client_request.get(
        '.organisation_dashboard',
        org_id=ORGANISATION_ID,
    )

    assert len(page.select('.browse-list-item')) == 3

    for i in range(0, 2):
        service_name = mock_get_organisation_services(mock_get_organisation['id'])[i]['name']
        service_id = mock_get_organisation_services(mock_get_organisation['id'])[i]['id']

        assert normalize_spaces(page.select('.browse-list-item')[i].text) == service_name
        if i > 1:
            assert normalize_spaces(
                page.select('.browse-list-item a')[i]['href']
            ) == '/services/{}'.format(service_id)
        else:
            assert page.select('.browse-list-item')[i].find('a') is None


def test_view_team_members(
    client_request,
    mocker,
    mock_get_organisation,
    mock_get_users_for_organisation,
    mock_get_invited_users_for_organisation,
    fake_uuid
):
    page = client_request.get(
        '.manage_org_users',
        org_id=ORGANISATION_ID,
    )

    for i in range(0, 2):
        assert normalize_spaces(
            page.select('.user-list-item .heading-small')[i].text
        ) == 'Test User {}'.format(i + 1)

    assert normalize_spaces(
        page.select('.tick-cross-list-edit-link')[1].text
    ) == 'Cancel invitation'


def test_invite_org_user(
    client_request,
    mocker,
    mock_get_organisation,
    sample_org_invite,
):

    mock_invite_org_user = mocker.patch(
        'app.org_invite_api_client.create_invite',
        return_value=InvitedOrgUser(**sample_org_invite)
    )

    client_request.post(
        '.invite_org_user',
        org_id=ORGANISATION_ID,
        _data={'email_address': 'test@example.gov.uk'}
    )

    mock_invite_org_user.assert_called_once_with(
        sample_org_invite['invited_by'],
        '{}'.format(ORGANISATION_ID),
        'test@example.gov.uk',
    )


def test_invite_org_user_errors_when_same_email_as_inviter(
    client_request,
    mocker,
    mock_get_organisation,
    sample_org_invite,
):
    new_org_user_data = {
        'email_address': 'test@user.gov.uk',
    }

    mock_invite_org_user = mocker.patch(
        'app.org_invite_api_client.create_invite',
        return_value=InvitedOrgUser(**sample_org_invite)
    )

    page = client_request.post(
        '.invite_org_user',
        org_id=ORGANISATION_ID,
        _data=new_org_user_data,
        _follow_redirects=True
    )

    assert mock_invite_org_user.called is False
    assert normalize_spaces(page.select_one('.error-message').text) == 'You can’t send an invitation to yourself'


def test_accepted_invite_when_user_already_logged_in(
    client_request,
    mock_check_org_invite_token
):
    page = client_request.get(
        'main.accept_org_invite',
        token='thisisnotarealtoken',
        follow_redirects=True,
        _expected_status=403,
    )
    assert 'This invite is for another email address.' in normalize_spaces(
        page.select_one('.banner-dangerous').text
    )


def test_cancelled_invite_opened_by_user(
    client,
    mock_check_org_cancelled_invite_token,
    mock_get_organisation,
    mock_get_user,
    fake_uuid
):
    response = client.get(url_for('main.accept_org_invite', token='thisisnotarealtoken'), follow_redirects=True)

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(
        page.select_one('h1').text
    ) == 'The invitation you were sent has been cancelled'
    assert normalize_spaces(
        page.select('main p')[0].text
    ) == 'Test User decided to cancel this invitation.'
    assert normalize_spaces(
        page.select('main p')[1].text
    ) == 'If you need access to Org 1, you’ll have to ask them to invite you again.'

    mock_get_user.assert_called_once_with(fake_uuid)
    mock_get_organisation.assert_called_once_with(ORGANISATION_ID)


def test_user_invite_already_accepted(
    client,
    mock_check_org_accepted_invite_token
):
    response = client.get(url_for('main.accept_org_invite', token='thisisnotarealtoken'))

    assert response.status_code == 302
    assert response.location == url_for(
        'main.organisation_dashboard',
        org_id=ORGANISATION_ID,
        _external=True
    )


def test_existing_user_invite_already_is_member_of_organisation(
    client,
    mock_check_org_invite_token,
    mock_get_user_by_email,
    mock_get_users_for_organisation,
    mock_accept_org_invite,
    mock_add_user_to_organisation,
):
    response = client.get(url_for('main.accept_org_invite', token='thisisnotarealtoken'))

    assert response.status_code == 302
    assert response.location == url_for(
        'main.organisation_dashboard',
        org_id=ORGANISATION_ID,
        _external=True
    )

    mock_accept_org_invite.assert_called_once_with(ORGANISATION_ID, ANY)
    mock_get_user_by_email.assert_called_once_with('invited_user@test.gov.uk')
    mock_get_users_for_organisation.assert_called_once_with(ORGANISATION_ID)


def test_existing_user_invite_not_a_member_of_organisation(
    client,
    mock_check_org_invite_token,
    mock_get_user_by_email,
    mock_get_users_for_organisation,
    mock_accept_org_invite,
    mock_add_user_to_organisation,
):
    response = client.get(url_for('main.accept_org_invite', token='thisisnotarealtoken'))

    assert response.status_code == 302
    assert response.location == url_for(
        'main.organisation_dashboard',
        org_id=ORGANISATION_ID,
        _external=True
    )

    mock_accept_org_invite.assert_called_once_with(ORGANISATION_ID, ANY)
    mock_get_user_by_email.assert_called_once_with('invited_user@test.gov.uk')
    mock_get_users_for_organisation.assert_called_once_with(ORGANISATION_ID)
    mock_add_user_to_organisation.assert_called_once_with(
        ORGANISATION_ID,
        '6ce466d0-fd6a-11e5-82f5-e0accb9d11a6'
    )


def test_user_accepts_invite(
    client,
    mock_check_org_invite_token,
    mock_dont_get_user_by_email,
    mock_get_users_for_organisation,
):
    response = client.get(url_for('main.accept_org_invite', token='thisisnotarealtoken'))

    assert response.status_code == 302
    assert response.location == url_for('main.register_from_org_invite', _external=True)

    mock_check_org_invite_token.assert_called_once_with('thisisnotarealtoken')
    mock_dont_get_user_by_email.assert_called_once_with('invited_user@test.gov.uk')
    mock_get_users_for_organisation.assert_called_once_with(ORGANISATION_ID)


def test_registration_from_org_invite_404s_if_user_not_in_session(
    client,
):
    response = client.get(url_for('main.register_from_org_invite'))
    assert response.status_code == 404


@pytest.mark.parametrize('data, error', [
    [{
        'name': 'Bad Mobile',
        'mobile_number': 'not good',
        'password': 'validPassword!'
    }, 'Must not contain letters or symbols'],
    [{
        'name': 'Bad Password',
        'mobile_number': '+44123412345',
        'password': 'password'
    }, 'Choose a password that’s harder to guess'],
])
def test_registration_from_org_invite_has_bad_data(
    client,
    sample_org_invite,
    data,
    error
):
    invited_org_user = InvitedOrgUser(**sample_org_invite)
    with client.session_transaction() as session:
        session['invited_org_user'] = invited_org_user.serialize()

    response = client.post(url_for('main.register_from_org_invite'), data=data)

    assert response.status_code == 200
    assert error in response.get_data(as_text=True)


@pytest.mark.parametrize('diff_data', [
    ['email_address'],
    ['organisation'],
    ['email_address', 'organisation']
])
def test_registration_from_org_invite_has_different_email_or_organisation(
    client,
    sample_org_invite,
    diff_data
):
    invited_org_user = InvitedOrgUser(**sample_org_invite)
    with client.session_transaction() as session:
        session['invited_org_user'] = invited_org_user.serialize()

    for data in diff_data:
        session['invited_org_user'][data] = 'different'

    response = client.post(url_for('main.register_from_org_invite'), data={
        'name': 'Test User',
        'mobile_number': '+4407700900460',
        'password': 'validPassword!',
        'email_address': session['invited_org_user']['email_address'],
        'organisation': session['invited_org_user']['organisation']
    })

    assert response.status_code == 400


def test_org_user_registers_with_email_already_in_use(
    client,
    sample_org_invite,
    mock_email_is_already_in_use,
    mock_get_user_by_email,
    mock_accept_org_invite,
    mock_add_user_to_organisation,
    mock_send_already_registered_email,
    mock_register_user
):
    invited_org_user = InvitedOrgUser(**sample_org_invite)
    with client.session_transaction() as session:
        session['invited_org_user'] = invited_org_user.serialize()

    response = client.post(url_for('main.register_from_org_invite'), data={
        'name': 'Test User',
        'mobile_number': '+4407700900460',
        'password': 'validPassword!',
        'email_address': session['invited_org_user']['email_address'],
        'organisation': session['invited_org_user']['organisation']
    })

    assert response.status_code == 302
    assert response.location == url_for('main.verify', _external=True)

    mock_get_user_by_email.assert_called_once_with(
        session['invited_org_user']['email_address']
    )
    assert mock_register_user.called is False
    assert mock_send_already_registered_email.called is False


def test_org_user_registration(
    client,
    sample_org_invite,
    mock_email_is_not_already_in_use,
    mock_register_user,
    mock_send_verify_code,
    mock_get_user_by_email,
    mock_send_verify_email,
    mock_accept_org_invite,
    mock_add_user_to_organisation,
):
    invited_org_user = InvitedOrgUser(**sample_org_invite)
    with client.session_transaction() as session:
        session['invited_org_user'] = invited_org_user.serialize()

    response = client.post(url_for('main.register_from_org_invite'), data={
        'name': 'Test User',
        'email_address': session['invited_org_user']['email_address'],
        'mobile_number': '+4407700900460',
        'password': 'validPassword!',
        'organisation': session['invited_org_user']['organisation']
    })

    assert response.status_code == 302
    assert response.location == url_for('main.verify', _external=True)

    mock_get_user_by_email.called is False
    mock_register_user.assert_called_once_with(
        'Test User',
        session['invited_org_user']['email_address'],
        '+4407700900460',
        'validPassword!',
        'sms_auth'
    )
    mock_send_verify_code.assert_called_once_with(
        '6ce466d0-fd6a-11e5-82f5-e0accb9d11a6',
        'sms',
        '+4407700900460',
    )


def test_verified_org_user_redirects_to_dashboard(
    client,
    sample_org_invite,
    mock_check_verify_code,
    mock_get_user,
    mock_activate_user,
    mock_login,
):
    invited_org_user = InvitedOrgUser(**sample_org_invite).serialize()
    with client.session_transaction() as session:
        session['expiry_date'] = str(datetime.utcnow() + timedelta(hours=1))
        session['user_details'] = {"email": invited_org_user['email_address'], "id": invited_org_user['id']}
        session['organisation_id'] = invited_org_user['organisation']

    response = client.post(url_for('main.verify'), data={'sms_code': '12345'})

    assert response.status_code == 302
    assert response.location == url_for(
        'main.organisation_dashboard',
        org_id=invited_org_user['organisation'],
        _external=True
    )


def test_organisation_settings(
    client_request,
    mock_get_organisation,
    organisation_one
):
    expected_rows = [
        'Label Value Action',
        'Organisation name Org 1 Change',
    ]

    page = client_request.get('.organisation_settings', org_id=organisation_one['id'])

    assert page.find('h1').text == 'Settings'
    rows = page.select('tr')
    assert len(rows) == len(expected_rows)
    for index, row in enumerate(expected_rows):
        assert row == " ".join(rows[index].text.split())
    mock_get_organisation.assert_called_with(organisation_one['id'])


def test_organisation_settings_for_platform_admin(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    organisation_one
):
    expected_rows = [
        'Label Value Action',
        'Organisation name Org 1 Change',

        'Label Value Action',
        'Organisation type Not set Change',
        'Crown organisation Yes Change',
        'Data sharing and financial agreement Not signed Change',
        'Default email branding GOV.UK Change',
        'Default letter branding No branding Change',
        'Known email domains None Change',
    ]

    client_request.login(platform_admin_user)
    page = client_request.get('.organisation_settings', org_id=organisation_one['id'])

    assert page.find('h1').text == 'Settings'
    rows = page.select('tr')
    assert len(rows) == len(expected_rows)
    for index, row in enumerate(expected_rows):
        assert row == " ".join(rows[index].text.split())
    mock_get_organisation.assert_called_with(organisation_one['id'])


@pytest.mark.parametrize('endpoint, expected_options, expected_selected', (
    (
        '.edit_organisation_type',
        (
            ('central', 'Central government'),
            ('local', 'Local government'),
            ('nhs', 'NHS'),
        ),
        None,
    ),
    (
        '.edit_organisation_crown_status',
        (
            ('crown', 'Yes'),
            ('non-crown', 'No'),
            ('unknown', 'Not sure'),
        ),
        'crown',
    ),
    (
        '.edit_organisation_agreement',
        (
            ('yes', (
                'Yes '
                'Users will be told their organisation has already signed the agreement'
            )),
            ('no', (
                'No '
                'Users will be prompted to sign the agreement before they can go live'
            )),
            ('unknown', (
                'No (but we have some service-specific agreements in place) '
                'Users won’t be prompted to sign the agreement'
            )),
        ),
        'no',
    ),
))
@pytest.mark.parametrize('user', (
    pytest.param(
        platform_admin_user,
    ),
    pytest.param(
        active_user_with_permissions,
        marks=pytest.mark.xfail
    ),
))
def test_view_organisation_settings(
    client_request,
    fake_uuid,
    organisation_one,
    mock_get_organisation,
    endpoint,
    expected_options,
    expected_selected,
    user,
):
    client_request.login(user(fake_uuid))

    page = client_request.get(endpoint, org_id=organisation_one['id'])

    radios = page.select('input[type=radio]')

    for index, option in enumerate(expected_options):
        label = page.select_one('label[for={}]'.format(radios[index]['id']))
        assert (
            radios[index]['value'],
            normalize_spaces(label.text),
        ) == option

    if expected_selected:
        assert page.select_one('input[checked]')['value'] == expected_selected
    else:
        assert not page.select_one('input[checked]')


@pytest.mark.parametrize('endpoint, post_data, expected_persisted', (
    (
        '.edit_organisation_type',
        {'organisation_type': 'central'},
        {'organisation_type': 'central'},
    ),
    (
        '.edit_organisation_type',
        {'organisation_type': 'local'},
        {'organisation_type': 'local'},
    ),
    (
        '.edit_organisation_type',
        {'organisation_type': 'nhs'},
        {'organisation_type': 'nhs'},
    ),
    (
        '.edit_organisation_crown_status',
        {'crown_status': 'crown'},
        {'crown': True},
    ),
    (
        '.edit_organisation_crown_status',
        {'crown_status': 'non-crown'},
        {'crown': False},
    ),
    (
        '.edit_organisation_crown_status',
        {'crown_status': 'unknown'},
        {'crown': None},
    ),
    (
        '.edit_organisation_agreement',
        {'agreement_signed': 'yes'},
        {'agreement_signed': True},
    ),
    (
        '.edit_organisation_agreement',
        {'agreement_signed': 'no'},
        {'agreement_signed': False},
    ),
    (
        '.edit_organisation_agreement',
        {'agreement_signed': 'unknown'},
        {'agreement_signed': None},
    ),
))
@pytest.mark.parametrize('user', (
    pytest.param(
        platform_admin_user,
    ),
    pytest.param(
        active_user_with_permissions,
        marks=pytest.mark.xfail
    ),
))
def test_update_organisation_settings(
    client_request,
    fake_uuid,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
    endpoint,
    post_data,
    expected_persisted,
    user,
):
    client_request.login(user(fake_uuid))

    client_request.post(
        endpoint,
        org_id=organisation_one['id'],
        _data=post_data,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.organisation_settings',
            org_id=organisation_one['id'],
            _external=True,
        ),
    )

    mock_update_organisation.assert_called_once_with(
        organisation_one['id'],
        **expected_persisted,
    )


@pytest.mark.parametrize('user', (
    pytest.param(
        platform_admin_user,
    ),
    pytest.param(
        active_user_with_permissions,
        marks=pytest.mark.xfail
    ),
))
def test_view_organisation_domains(
    mocker,
    client_request,
    fake_uuid,
    user,
):
    client_request.login(user(fake_uuid))

    mocker.patch(
        'app.organisations_client.get_organisation',
        side_effect=lambda org_id: organisation_json(
            org_id,
            'Org 1',
            domains=['example.gov.uk', 'test.example.gov.uk'],
        )
    )

    page = client_request.get(
        'main.edit_organisation_domains',
        org_id=ORGANISATION_ID,
    )

    assert [textbox['value'] for textbox in page.select('input[type=text]')] == [
        'example.gov.uk',
        'test.example.gov.uk',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
    ]


@pytest.mark.parametrize('post_data, expected_persisted', (
    (
        {
            'domains-0': 'example.gov.uk',
            'domains-2': 'example.gov.uk',
            'domains-3': 'EXAMPLE.GOV.UK',
            'domains-5': 'test.gov.uk',
        },
        {
            'domains': [
                'example.gov.uk',
                'test.gov.uk',
            ]
        }
    ),
    (
        {
            'domains-0': '',
            'domains-1': '',
            'domains-2': '',
        },
        {
            'domains': []
        }
    ),
))
@pytest.mark.parametrize('user', (
    pytest.param(
        platform_admin_user,
    ),
    pytest.param(
        active_user_with_permissions,
        marks=pytest.mark.xfail
    ),
))
def test_update_organisation_domains(
    client_request,
    fake_uuid,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
    post_data,
    expected_persisted,
    user,
):
    client_request.login(user(fake_uuid))

    client_request.post(
        'main.edit_organisation_domains',
        org_id=ORGANISATION_ID,
        _data=post_data,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.organisation_settings',
            org_id=organisation_one['id'],
            _external=True,
        ),
    )

    mock_update_organisation.assert_called_once_with(
        ORGANISATION_ID,
        **expected_persisted,
    )


def test_update_organisation_name(
    logged_in_platform_admin_client,
    organisation_one,
    mock_get_organisation,
    mock_organisation_name_is_unique
):
    response = logged_in_platform_admin_client.post(
        url_for('.edit_organisation_name', org_id=organisation_one['id']),
        data={'name': 'TestNewOrgName'}
    )

    assert response.status_code == 302
    assert response.location == url_for(
        '.confirm_edit_organisation_name',
        org_id=organisation_one['id'],
        _external=True
    )
    assert mock_organisation_name_is_unique.called


def test_update_organisation_with_incorrect_input(
    logged_in_platform_admin_client,
    organisation_one,
    mock_get_organisation,
):
    response = logged_in_platform_admin_client.post(
        url_for('.edit_organisation_name', org_id=organisation_one['id']),
        data={'name': ''}
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(
        page.select_one('.error-message').text
    ) == "Can’t be empty"


def test_update_organisation_with_non_unique_name(
    logged_in_platform_admin_client,
    organisation_one,
    mock_get_organisation,
    mock_organisation_name_is_not_unique
):
    response = logged_in_platform_admin_client.post(
        url_for('.edit_organisation_name', org_id=organisation_one['id']),
        data={'name': 'TestNewOrgName'}
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(
        page.select_one('.error-message').text
    ) == 'This organisation name is already in use'

    assert mock_organisation_name_is_not_unique.called


def test_confirm_update_organisation(
    logged_in_platform_admin_client,
    organisation_one,
    mock_get_organisation,
    mock_verify_password,
    mock_update_organisation,
    mocker
):
    with logged_in_platform_admin_client.session_transaction() as session:
        session['organisation_name_change'] = 'newName'

    response = logged_in_platform_admin_client.post(
        url_for(
            '.confirm_edit_organisation_name',
            org_id=organisation_one['id'],
            data={'password', 'validPassword'}
        )
    )

    assert response.status_code == 302
    assert response.location == url_for('.organisation_settings', org_id=organisation_one['id'], _external=True)

    mock_update_organisation.assert_called_with(
        organisation_one['id'],
        name=session['organisation_name_change']
    )


def test_confirm_update_organisation_with_incorrect_password(
    logged_in_platform_admin_client,
    organisation_one,
    mock_get_organisation,
    mocker
):
    with logged_in_platform_admin_client.session_transaction() as session:
        session['organisation_name_change'] = 'newName'

    mocker.patch('app.user_api_client.verify_password', return_value=False)

    response = logged_in_platform_admin_client.post(
        url_for(
            '.confirm_edit_organisation_name',
            org_id=organisation_one['id']
        )
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(
        page.select_one('.error-message').text
    ) == 'Invalid password'


def test_confirm_update_organisation_with_name_already_in_use(
    logged_in_platform_admin_client,
    organisation_one,
    mock_get_organisation,
    mock_verify_password,
    mocker
):
    with logged_in_platform_admin_client.session_transaction() as session:
        session['organisation_name_change'] = 'newName'

    mocker.patch(
        'app.organisations_client.update_organisation_name',
        side_effect=HTTPError(
            response=Mock(
                status_code=400,
                json={'result': 'error', 'message': 'Organisation name already exists'}
            ),
            message="Organisation name already exists"
        )
    )

    response = logged_in_platform_admin_client.post(
        url_for(
            '.confirm_edit_organisation_name',
            org_id=organisation_one['id']
        )
    )

    assert response.status_code == 302
    assert response.location == url_for('main.edit_organisation_name', org_id=organisation_one['id'], _external=True)

from unittest.mock import Mock

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from notifications_python_client.errors import HTTPError

from tests import organisation_json, service_json
from tests.conftest import (
    ORGANISATION_ID,
    SERVICE_ONE_ID,
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


def test_organisation_services_shows_live_services_only(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
    fake_uuid,
):
    mocker.patch(
        'app.organisations_client.get_organisation_services',
        return_value=[
            service_json(id_='1', name='1', restricted=False, active=True),  # live
            service_json(id_='2', name='2', restricted=True, active=True),  # trial
            service_json(id_='3', name='3', restricted=True, active=False),  # trial, now archived
            service_json(id_='4', name='4', restricted=False, active=False),  # was live, now archived
            service_json(id_=SERVICE_ONE_ID, name='5', restricted=False, active=True),  # live, member of
        ]
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get('.organisation_dashboard', org_id=ORGANISATION_ID)

    services = page.select('.browse-list-item')
    assert len(services) == 2

    assert normalize_spaces(services[0].text) == '1'
    assert normalize_spaces(services[1].text) == '5'
    assert services[0].find('a') is None
    assert services[1].find('a')['href'] == url_for('main.service_dashboard', service_id=SERVICE_ONE_ID)


def test_organisation_trial_mode_services_shows_all_services(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mocker,
    fake_uuid,
):
    mocker.patch(
        'app.organisations_client.get_organisation_services',
        return_value=[
            service_json(id_='1', name='1', restricted=False, active=True),  # live
            service_json(id_='2', name='2', restricted=True, active=True),  # trial
            service_json(id_='3', name='3', restricted=True, active=False),  # archived
        ]
    )

    client_request.login(platform_admin_user)
    page = client_request.get(
        '.organisation_trial_mode_services',
        org_id=ORGANISATION_ID,
        _test_page_title=False
    )

    services = page.select('.browse-list-item')
    assert len(services) == 2

    assert normalize_spaces(services[0].text) == '2'
    assert normalize_spaces(services[1].text) == '3'
    assert services[0].find('a')['href'] == url_for('main.service_dashboard', service_id='2')
    assert services[1].find('a')['href'] == url_for('main.service_dashboard', service_id='3')


def test_organisation_trial_mode_services_doesnt_work_if_not_platform_admin(
    client_request,
    mock_get_organisation,
):
    client_request.get(
        '.organisation_trial_mode_services',
        org_id=ORGANISATION_ID,
        _expected_status=403
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
        'Request to go live notes None Change',
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


def test_get_edit_organisation_go_live_notes_page(
    logged_in_platform_admin_client,
    mock_get_organisation,
    organisation_one,
):
    response = logged_in_platform_admin_client.get(
        url_for(
            '.edit_organisation_go_live_notes',
            org_id=organisation_one['id']
        )
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.find('textarea', id='request_to_go_live_notes')


@pytest.mark.parametrize('input_note,saved_note', [
    ('Needs permission', 'Needs permission'),
    ('  ', None)
])
def test_post_edit_organisation_go_live_notes_updates_go_live_notes(
    logged_in_platform_admin_client,
    mock_get_organisation,
    mock_update_organisation,
    organisation_one,
    input_note,
    saved_note,
):
    response = logged_in_platform_admin_client.post(
        url_for(
            '.edit_organisation_go_live_notes',
            org_id=organisation_one['id'],
        ),
        data={'request_to_go_live_notes': input_note}
    )

    mock_update_organisation.assert_called_once_with(
        organisation_one['id'],
        request_to_go_live_notes=saved_note
    )
    assert response.status_code == 302
    assert response.location == url_for(
        '.organisation_settings',
        org_id=organisation_one['id'],
        _external=True
    )

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from tests.conftest import normalize_spaces, ORGANISATION_ID


@pytest.mark.parametrize('endpoint', ['.organisations', '.add_organisation'])
def test_global_organisation_pages_are_platform_admin_only(client_request, endpoint):
    client_request.get(
        endpoint,
        _expected_status=403,
        _test_page_title=False
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
    assert normalize_spaces((page.select('a.browse-list-link')[-1]).text) == 'Create an organisation'


def test_create_new_organisation(
    logged_in_platform_admin_client,
    mocker
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


def test_view_organisation_shows_the_correct_organisation(
    logged_in_client,
    mocker
):
    org = {'id': ORGANISATION_ID, 'name': 'Test 1', 'active': True}
    mocker.patch(
        'app.organisations_client.get_organisation', return_value=org
    )
    mocker.patch(
        'app.organisations_client.get_organisation_services', return_value=[]
    )

    response = logged_in_client.get(
        url_for('.organisation_dashboard', org_id=ORGANISATION_ID)
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(page.select_one('.heading-large').text) == org['name']


def test_edit_organisation_shows_the_correct_organisation(
    logged_in_client,
    mocker
):
    org = {'id': ORGANISATION_ID, 'name': 'Test 1', 'active': True}
    mocker.patch(
        'app.organisations_client.get_organisation', return_value=org
    )

    response = logged_in_client.get(
        url_for('.update_organisation', org_id=ORGANISATION_ID)
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.select_one('#name').attrs.get('value') == org['name']


def test_update_organisation(
    logged_in_client,
    mocker,
):
    org = {'name': 'new name'}

    mocker.patch(
        'app.organisations_client.get_organisation', return_value=org
    )
    mock_update_organisation = mocker.patch(
        'app.organisations_client.update_organisation'
    )

    logged_in_client.post(
        url_for('.update_organisation', org_id=ORGANISATION_ID),
        content_type='multipart/form-data',
        data=org
    )

    assert mock_update_organisation.called
    mock_update_organisation.assert_called_once_with(
        org_id=ORGANISATION_ID,
        name=org['name']
    )


def test_organisation_dashboard_shows_services(
    logged_in_client,
    mock_get_organisation,
    mock_get_organisation_services,
    mocker,
):
    response = logged_in_client.get(
        url_for('.organisation_dashboard', org_id=ORGANISATION_ID),
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert len(page.select('.browse-list-item')) == 3

    for i in range(0, 3):
        service_name = mock_get_organisation_services(ORGANISATION_ID)[i]['name']
        service_id = mock_get_organisation_services(ORGANISATION_ID)[i]['id']

        assert normalize_spaces(page.select('.browse-list-item')[i].text) == service_name
        assert normalize_spaces(
            page.select('.browse-list-item a')[i]['href']
        ) == '/services/{}'.format(service_id)


def test_view_team_members(
    logged_in_client,
    mocker,
    mock_get_organisation,
    mock_get_users_for_organisation,
    mock_get_invited_users_for_organisation,
):
    response = logged_in_client.get(
        url_for('.manage_org_users', org_id=ORGANISATION_ID),
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    for i in range(0, 2):
        assert normalize_spaces(
            page.select('.user-list-item .heading-small')[i].text
        ) == 'Test User {}'.format(i + 1)

    assert normalize_spaces(
        page.select('.tick-cross-list-edit-link')[1].text
    ) == 'Cancel invitation'

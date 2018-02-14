from bs4 import BeautifulSoup
from flask import url_for

from tests.conftest import (
    normalize_spaces
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


def test_view_organisation_shows_the_correct_organisation(
    logged_in_platform_admin_client,
    fake_uuid,
    mocker
):
    org = {'id': fake_uuid, 'name': 'Test 1', 'active': True}
    mocker.patch(
        'app.organisations_client.get_organisation', return_value=org
    )
    mocker.patch(
        'app.organisations_client.get_organisation_services', return_value=[]
    )

    response = logged_in_platform_admin_client.get(
        url_for('.organisation_dashboard', org_id=fake_uuid)
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(page.select_one('.heading-large').text) == org['name']


def test_edit_organisation_shows_the_correct_organisation(
    logged_in_platform_admin_client,
    fake_uuid,
    mocker
):
    org = {'id': fake_uuid, 'name': 'Test 1', 'active': True}
    mocker.patch(
        'app.organisations_client.get_organisation', return_value=org
    )

    response = logged_in_platform_admin_client.get(
        url_for('.update_organisation', org_id=fake_uuid)
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.select_one('#name').attrs.get('value') == org['name']


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


def test_update_organisation(
    logged_in_platform_admin_client,
    mocker,
    fake_uuid,
):
    org = {'name': 'new name'}

    mocker.patch(
        'app.organisations_client.get_organisation', return_value=org
    )
    mock_update_organisation = mocker.patch(
        'app.organisations_client.update_organisation'
    )

    logged_in_platform_admin_client.post(
        url_for('.update_organisation', org_id=fake_uuid),
        content_type='multipart/form-data',
        data=org
    )

    assert mock_update_organisation.called
    mock_update_organisation.assert_called_once_with(
        org_id=fake_uuid,
        name=org['name']
    )


def test_organisation_services_show(
    logged_in_platform_admin_client,
    mock_get_organisation,
    mock_get_organisation_services,
    mocker,
    fake_uuid,
):
    response = logged_in_platform_admin_client.get(
        url_for('.organisation_dashboard', org_id=mock_get_organisation['id']),
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert len(page.select('.browse-list-item')) == 3

    for i in range(0, 3):
        service_name = mock_get_organisation_services(mock_get_organisation['id'])[i]['name']
        service_id = mock_get_organisation_services(mock_get_organisation['id'])[i]['id']

        assert normalize_spaces(page.select('.browse-list-item')[i].text) == service_name
        assert normalize_spaces(
            page.select('.browse-list-item a')[i]['href']
        ) == '/services/{}'.format(service_id)

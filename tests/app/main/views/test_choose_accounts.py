import pytest
from bs4 import BeautifulSoup
from flask import url_for
from tests.conftest import normalize_spaces


SAMPLE_DATA = {
    'organisations': [
        {
            'name': 'org_1',
            'id': 'o1',
            'services': [
                {'name': 'org_service_1', 'id': 'os1'},
                {'name': 'org_service_2', 'id': 'os2'},
                {'name': 'org_service_3', 'id': 'os3'},
            ]
        },
        {
            'name': 'org_2',
            'id': 'o2',
            'services': [
                {'name': 'org_service_4', 'id': 'os4'},
            ]
        },
        {
            'name': 'org_3',
            'id': 'o3',
            'services': []
        }
    ],
    'services_without_organisations': [
        {'name': 'service_1', 'id': 's1'},
        {'name': 'service_2', 'id': 's2'},
        {'name': 'service_3', 'id': 's3'},
    ]
}


@pytest.fixture
def mock_get_orgs_and_services(mocker):
    return mocker.patch(
        'app.user_api_client.get_organisations_and_services_for_user',
        return_value=SAMPLE_DATA
    )


def test_choose_account_should_show_choose_accounts_page(
    client_request,
    mock_get_orgs_and_services
):
    resp = client_request.get('main.choose_account')
    page = resp.find('div', {'id': 'content'}).main

    assert normalize_spaces(page.h1.text) == 'Choose account'


def test_choose_account_should_show_choose_accounts_page_if_no_services(
    client_request,
    mock_get_orgs_and_services
):
    mock_get_orgs_and_services.return_value = {
        'organisations': [],
        'services_without_organisations': []
    }
    resp = client_request.get('main.choose_account')
    page = resp.find('div', {'id': 'content'}).main

    links = page.findAll('a')
    assert len(links) == 1
    add_service_link = links[0]
    assert normalize_spaces(page.h1.text) == 'Choose account'
    assert normalize_spaces(add_service_link.text) == 'Add a new service…'
    assert add_service_link['href'] == url_for('main.add_service')


def test_choose_account_should_show_back_to_service_link(
    client_request,
    mock_get_orgs_and_services
):
    resp = client_request.get('main.choose_account')

    page = resp.find('div', {'id': 'content'})
    back_to_service_link = page.find('div', {'class': 'navigation-service'}).a

    assert back_to_service_link['href'] == url_for('main.show_accounts_or_dashboard')
    assert back_to_service_link.text == 'Back to service one'


def test_choose_account_should_not_show_back_to_service_link_if_no_service_in_session(
    client,
    client_request,
    mock_get_orgs_and_services
):
    with client.session_transaction() as session:
        session['service_id'] = None
    page = client_request.get('main.choose_account')

    assert len(page.select('.navigation-service a')) == 0


def test_show_accounts_or_dashboard_redirects_if_only_one_service(
    logged_in_client,
    mock_login,
    api_user_active,
    mock_get_services_with_one_service,
):
    response = logged_in_client.get(url_for('main.show_accounts_or_dashboard'))

    service = mock_get_services_with_one_service.side_effect()['data'][0]
    assert response.status_code == 302
    assert response.location == url_for('main.service_dashboard', service_id=service['id'], _external=True)


def test_show_accounts_or_dashboard_redirects_if_multiple_services(
    logged_in_client,
    mock_login,
    api_user_active,
):
    response = logged_in_client.get(url_for('main.show_accounts_or_dashboard'))

    assert response.status_code == 302
    assert response.location == url_for('main.choose_account', _external=True)


def test_show_accounts_or_dashboard_redirects_if_service_in_session(
    logged_in_client,
    mock_login,
    api_user_active,
):
    with logged_in_client.session_transaction() as session:
        session['service_id'] = '147ad62a-2951-4fa1-9ca0-093cd1a52c52'
    response = logged_in_client.get(url_for('main.show_accounts_or_dashboard'))

    assert response.status_code == 302
    assert response.location == url_for(
        'main.service_dashboard',
        service_id='147ad62a-2951-4fa1-9ca0-093cd1a52c52',
        _external=True
    )


def test_show_accounts_or_dashboard_redirects_if_not_logged_in(
    logged_in_client,
    app_
):
    response = logged_in_client.get(url_for('main.show_accounts_or_dashboard'))
    assert response.status_code == 302
    assert url_for('main.index', _external=True) in response.location

import pytest
from bs4 import BeautifulSoup
from flask import url_for

from tests.conftest import (
    SERVICE_ONE_ID,
    normalize_spaces,
    service_one,
    service_two,
)

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

    assert normalize_spaces(page.h1.text) == 'Choose service'
    outer_list_items = page.nav.ul.find_all('li', recursive=False)

    assert len(outer_list_items) == 6

    # first org
    assert outer_list_items[0].a.text == 'org_1'
    assert outer_list_items[0].a['href'] == url_for('.organisation_dashboard', org_id='o1')
    outer_list_orgs = outer_list_items[0].ul
    assert ' '.join(outer_list_orgs.stripped_strings) == 'org_service_1 org_service_2 org_service_3'

    # second org
    assert outer_list_items[1].a.text == 'org_2'
    assert outer_list_items[1].a['href'] == url_for('.organisation_dashboard', org_id='o2')
    outer_list_orgs = outer_list_items[1].ul
    assert ' '.join(outer_list_orgs.stripped_strings) == 'org_service_4'

    # third org
    assert outer_list_items[2].a.text == 'org_3'
    assert outer_list_items[2].a['href'] == url_for('.organisation_dashboard', org_id='o3')
    assert not outer_list_items[2].ul  # org 3 has no services

    # orphaned services
    assert outer_list_items[3].a.text == 'service_1'
    assert outer_list_items[3].a['href'] == url_for('.service_dashboard', service_id='s1')
    assert outer_list_items[4].a.text == 'service_2'
    assert outer_list_items[4].a['href'] == url_for('.service_dashboard', service_id='s2')
    assert outer_list_items[5].a.text == 'service_3'
    assert outer_list_items[5].a['href'] == url_for('.service_dashboard', service_id='s3')


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
    assert normalize_spaces(page.h1.text) == 'Choose service'
    assert normalize_spaces(add_service_link.text) == 'Add a new service'
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


def test_choose_account_should_not_show_back_to_service_link_if_not_signed_in(
    client,
    mock_get_service,
):
    with client.session_transaction() as session:
        session['service_id'] = SERVICE_ONE_ID
    response = client.get(url_for('main.sign_in'))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.select_one('h1').text == 'Sign in'  # We’re not signed in
    assert page.select_one('.navigation-service a') is None


@pytest.mark.parametrize('service, expected_status, page_text', (
    (service_one, 200, (
        'Test Service   Switch service '
        ''
        'Dashboard '
        'Templates '
        'Team members'
    )),
    (service_two, 403, (
        # Page has no ‘back to’ link
        '403 '
        'You do not have permission to view this page.'
    )),
))
def test_should_not_show_back_to_service_if_user_doesnt_belong_to_service(
    client_request,
    api_user_active,
    fake_uuid,
    mock_get_service,
    mock_get_service_template,
    mock_get_template_folders,
    service,
    expected_status,
    page_text,
):
    mock_get_service.return_value = service(api_user_active)

    page = client_request.get(
        'main.view_template',
        service_id=mock_get_service.return_value['id'],
        template_id=fake_uuid,
        _expected_status=expected_status,
    )

    assert normalize_spaces(
        page.select_one('#content').text
    ).startswith(
        normalize_spaces(page_text)
    )

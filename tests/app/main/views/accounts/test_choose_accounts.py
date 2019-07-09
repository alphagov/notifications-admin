import uuid
from itertools import repeat

import pytest
from bs4 import BeautifulSoup
from flask import url_for

from tests.conftest import (
    SERVICE_ONE_ID,
    SERVICE_TWO_ID,
    normalize_spaces,
    service_one,
    service_two,
)

OS1, OS2, OS3, S1, S2, S3 = repeat(uuid.uuid4(), 6)

SAMPLE_DATA = {
    'organisations': [
        {
            'name': 'org_1',
            'id': 'o1',
            'count_of_live_services': 1,
        },
        {
            'name': 'org_2',
            'id': 'o2',
            'count_of_live_services': 2,
        },
        {
            'name': 'org_3',
            'id': 'o3',
            'count_of_live_services': 0,
        }
    ],
    'services': [
        {
            'name': 'org_service_1',
            'id': OS1,
            'restricted': False,
            'organisation': 'o1',
        },
        {
            'name': 'org_service_2',
            'id': OS2,
            'restricted': False,
            'organisation': 'o1',
        },
        {
            'name': 'org_service_3',
            'id': OS3,
            'restricted': True,
            'organisation': 'o1',
        },
        {
            'name': 'service_1',
            'id': S1,
            'restricted': False,
            'organisation': None,
        },
        {
            'name': 'service_2',
            'id': S2,
            'restricted': False,
            'organisation': None,
        },
        {
            'name': 'service_3',
            'id': S3,
            'restricted': True,
            'organisation': None,
        },
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
    mock_get_non_empty_organisations_and_services_for_user,
    mock_get_organisation,
):
    resp = client_request.get('main.choose_account')
    page = resp.find('div', {'id': 'content'}).main

    assert normalize_spaces(page.h1.text) == 'Choose service'
    outer_list_items = page.select('nav ul')[0].select('li')

    assert len(outer_list_items) == 7

    # first org
    assert outer_list_items[0].a.text == 'Org 1'
    assert outer_list_items[0].a['href'] == url_for('.organisation_dashboard', org_id='o1')
    assert normalize_spaces(outer_list_items[0].select_one('.browse-list-hint').text) == (
        '1 live service'
    )

    # second org
    assert outer_list_items[1].a.text == 'Org 2'
    assert outer_list_items[1].a['href'] == url_for('.organisation_dashboard', org_id='o2')
    assert normalize_spaces(outer_list_items[1].select_one('.browse-list-hint').text) == (
        '2 live services'
    )

    # third org
    assert outer_list_items[2].a.text == 'Org 3'
    assert outer_list_items[2].a['href'] == url_for('.organisation_dashboard', org_id='o3')
    assert normalize_spaces(outer_list_items[2].select_one('.browse-list-hint').text) == (
        '0 live services'
    )

    # orphaned live services
    assert outer_list_items[3].a.text == 'Service 1'
    assert outer_list_items[3].a['href'] == url_for('.service_dashboard', service_id=SERVICE_TWO_ID)
    assert outer_list_items[4].a.text == 'service one'
    assert outer_list_items[4].a['href'] == url_for('.service_dashboard', service_id='12345')

    # orphaned trial services
    trial_services_list_items = page.select('nav ul')[1].select('li')
    assert len(trial_services_list_items) == 3
    assert trial_services_list_items[0].a.text == 'service three'
    assert trial_services_list_items[0].a['href'] == url_for('.service_dashboard', service_id='abcde')
    assert trial_services_list_items[1].a.text == 'service three'
    assert trial_services_list_items[1].a['href'] == url_for('.service_dashboard', service_id='abcde')

    assert mock_get_organisation.call_args_list == []


def test_choose_account_should_show_choose_accounts_page_if_no_services(
    client_request,
    mock_get_orgs_and_services,
    mock_get_organisation,
    mock_get_organisation_services,
):
    mock_get_orgs_and_services.return_value = {
        'organisations': [],
        'services': []
    }
    resp = client_request.get('main.choose_account')
    page = resp.find('div', {'id': 'content'}).main

    links = page.findAll('a')
    assert len(links) == 1
    add_service_link = links[0]
    assert normalize_spaces(page.h1.text) == 'Choose service'
    assert normalize_spaces(add_service_link.text) == 'Add a new service'
    assert add_service_link['href'] == url_for('main.add_service')


def test_choose_account_should_should_organisations_link_for_platform_admin(
    client_request,
    platform_admin_user,
    mock_get_organisations,
    mock_get_orgs_and_services,
    mock_get_organisation_services,
    mock_get_service_and_organisation_counts,
):
    client_request.login(platform_admin_user)

    page = client_request.get('main.choose_account')

    first_item = page.select_one('.browse-list-item')
    first_link = first_item.select_one('a')
    first_hint = first_item.select_one('.browse-list-hint')
    assert first_link.text == 'All organisations'
    assert first_link['href'] == url_for('main.organisations')
    assert normalize_spaces(first_hint.text) == '3 organisations, 9,999 live services'


def test_choose_account_should_show_back_to_service_link(
    client_request,
    mock_get_orgs_and_services,
    mock_get_organisation,
    mock_get_organisation_services,
):
    resp = client_request.get('main.choose_account')

    page = resp.find('div', {'id': 'content'})
    back_to_service_link = page.find('div', {'class': 'navigation-service'}).a

    assert back_to_service_link['href'] == url_for('main.show_accounts_or_dashboard')
    assert back_to_service_link.text == 'Back to service one'


def test_choose_account_should_not_show_back_to_service_link_if_no_service_in_session(
    client,
    client_request,
    mock_get_orgs_and_services,
    mock_get_organisation,
    mock_get_organisation_services,
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


@pytest.mark.parametrize('active', (
    False,
    pytest.param(True, marks=pytest.mark.xfail(raises=AssertionError)),
))
def test_choose_account_should_not_show_back_to_service_link_if_service_archived(
    client_request,
    service_one,
    mock_get_orgs_and_services,
    mock_get_organisation,
    mock_get_organisation_services,
    active,
):
    service_one['active'] = active
    with client_request.session_transaction() as session:
        session['service_id'] = service_one['id']
    page = client_request.get('main.choose_account')

    assert normalize_spaces(page.select_one('h1').text) == 'Choose service'
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
        _test_page_title=False,
    )

    assert normalize_spaces(
        page.select_one('#content').text
    ).startswith(
        normalize_spaces(page_text)
    )

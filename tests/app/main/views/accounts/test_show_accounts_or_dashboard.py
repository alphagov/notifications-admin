import pytest
from flask import url_for

from tests import user_json


def user_with_orgs_and_services(num_orgs, num_services, platform_admin=False):
    return user_json(
        name='leo',
        organisations=['org{}'.format(i) for i in range(1, num_orgs + 1)],
        services=['service{}'.format(i) for i in range(1, num_services + 1)],
        platform_admin=platform_admin
    )


@pytest.mark.parametrize('num_orgs,num_services,endpoint,endpoint_kwargs', [
    (0, 0, '.choose_account', {}),
    (0, 2, '.choose_account', {}),

    # assumption is that live service is part of user’s organisation
    # – real users shouldn’t have orphaned live services, or access to
    # services belonging to other organisations
    (1, 1, '.organisation_dashboard', {'org_id': 'org1'}),

    (2, 0, '.choose_account', {}),
    (0, 1, '.service_dashboard', {'service_id': 'service1'}),
    (1, 0, '.organisation_dashboard', {'org_id': 'org1'}),
])
def test_show_accounts_or_dashboard_redirects_to_choose_account_or_service_dashboard(
    client_request,
    mock_get_organisations_and_services_for_user,
    num_orgs,
    num_services,
    endpoint,
    endpoint_kwargs
):
    client_request.login(user_with_orgs_and_services(num_orgs=num_orgs, num_services=num_services))

    client_request.get(
        'main.show_accounts_or_dashboard',
        _expected_redirect=url_for(endpoint, **endpoint_kwargs)
    )


def test_show_accounts_or_dashboard_redirects_if_service_in_session(client_request, mock_get_service):
    client_request.login(user_with_orgs_and_services(num_orgs=1, num_services=1))
    with client_request.session_transaction() as session:
        session['service_id'] = 'service1'
        session['organisation_id'] = None

    client_request.get(
        '.show_accounts_or_dashboard',
        _expected_redirect=url_for(
            'main.service_dashboard',
            service_id='service1',
        ),
    )


def test_show_accounts_or_dashboard_redirects_if_org_in_session(client_request):
    client_request.login(user_with_orgs_and_services(num_orgs=1, num_services=1))
    with client_request.session_transaction() as session:
        session['service_id'] = None
        session['organisation_id'] = 'org1'

    client_request.get(
        '.show_accounts_or_dashboard',
        _expected_redirect=url_for(
            'main.organisation_dashboard',
            org_id='org1',
        ),
    )


def test_show_accounts_or_dashboard_doesnt_redirect_to_service_dashboard_if_user_not_part_of_service_in_session(
    client_request,
    mock_get_organisations_and_services_for_user,
    mock_get_service
):
    client_request.login(user_with_orgs_and_services(num_orgs=1, num_services=1))
    with client_request.session_transaction() as session:
        session['service_id'] = 'service2'
        session['organisation_id'] = None

    client_request.get(
        '.show_accounts_or_dashboard',
        _expected_redirect=url_for('main.organisation_dashboard', org_id='org1')
    )


def test_show_accounts_or_dashboard_doesnt_redirect_to_org_dashboard_if_user_not_part_of_org_in_session(
    client_request,
    mock_get_organisations_and_services_for_user,
):
    client_request.login(user_with_orgs_and_services(num_orgs=1, num_services=1))
    with client_request.session_transaction() as session:
        session['service_id'] = None
        session['organisation_id'] = 'org2'

    client_request.get(
        '.show_accounts_or_dashboard',
        _expected_redirect=url_for('main.organisation_dashboard', org_id='org1')
    )


def test_show_accounts_or_dashboard_redirects_if_not_logged_in(
    client_request,
    notify_admin,
):
    client_request.logout()
    client_request.get(
        'main.show_accounts_or_dashboard',
        _expected_redirect=url_for('main.index'),
    )


def test_show_accounts_or_dashboard_redirects_to_service_dashboard_if_platform_admin(
    client_request,
    mocker,
    mock_get_service
):
    client_request.login(user_with_orgs_and_services(num_orgs=1, num_services=1, platform_admin=True))
    with client_request.session_transaction() as session:
        session['service_id'] = 'service2'
        session['organisation_id'] = None

    client_request.get(
        '.show_accounts_or_dashboard',
        _expected_redirect=url_for(
            'main.service_dashboard',
            service_id='service2',
        ),
    )


def test_show_accounts_or_dashboard_redirects_to_org_dashboard_if_platform_admin(
    client_request,
):
    client_request.login(user_with_orgs_and_services(num_orgs=1, num_services=1, platform_admin=True))
    with client_request.session_transaction() as session:
        session['service_id'] = None
        session['organisation_id'] = 'org2'

    client_request.get(
        '.show_accounts_or_dashboard',
        _expected_redirect=url_for(
            'main.organisation_dashboard',
            org_id='org2',
        ),
    )

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
    (1, 1, '.choose_account', {}),
    (2, 0, '.choose_account', {}),
    (0, 1, '.service_dashboard', {'service_id': 'service1'}),
    (1, 0, '.organisation_dashboard', {'org_id': 'org1'}),
])
def test_show_accounts_or_dashboard_redirects_to_choose_account_or_service_dashboard(
    client,
    mocker,
    num_orgs,
    num_services,
    endpoint,
    endpoint_kwargs
):
    client.login(user_with_orgs_and_services(num_orgs=num_orgs, num_services=num_services), mocker=mocker)

    response = client.get(url_for('main.show_accounts_or_dashboard'))

    assert response.status_code == 302
    assert response.location == url_for(endpoint, _external=True, **endpoint_kwargs)


def test_show_accounts_or_dashboard_redirects_if_service_in_session(client, mocker, mock_get_service):
    client.login(user_with_orgs_and_services(num_orgs=1, num_services=1), mocker=mocker)
    with client.session_transaction() as session:
        session['service_id'] = 'service1'
        session['organisation_id'] = None

    response = client.get(url_for('.show_accounts_or_dashboard'))

    assert response.status_code == 302
    assert response.location == url_for(
        'main.service_dashboard',
        service_id='service1',
        _external=True
    )


def test_show_accounts_or_dashboard_redirects_if_org_in_session(client, mocker):
    client.login(user_with_orgs_and_services(num_orgs=1, num_services=1), mocker=mocker)
    with client.session_transaction() as session:
        session['service_id'] = None
        session['organisation_id'] = 'org1'

    response = client.get(url_for('.show_accounts_or_dashboard'))

    assert response.status_code == 302
    assert response.location == url_for(
        'main.organisation_dashboard',
        org_id='org1',
        _external=True
    )


def test_show_accounts_or_dashboard_doesnt_redirect_to_service_dashboard_if_user_not_part_of_service_in_session(
    client,
    mocker,
    mock_get_service
):
    client.login(user_with_orgs_and_services(num_orgs=1, num_services=1), mocker=mocker)
    with client.session_transaction() as session:
        session['service_id'] = 'service2'
        session['organisation_id'] = None

    response = client.get(url_for('.show_accounts_or_dashboard'))

    assert response.status_code == 302
    assert response.location == url_for('main.choose_account', _external=True)


def test_show_accounts_or_dashboard_doesnt_redirect_to_org_dashboard_if_user_not_part_of_org_in_session(
    client,
    mocker
):
    client.login(user_with_orgs_and_services(num_orgs=1, num_services=1), mocker=mocker)
    with client.session_transaction() as session:
        session['service_id'] = None
        session['organisation_id'] = 'org2'

    response = client.get(url_for('.show_accounts_or_dashboard'))

    assert response.status_code == 302
    assert response.location == url_for('main.choose_account', _external=True)


def test_show_accounts_or_dashboard_redirects_if_not_logged_in(
    client,
    app_
):
    response = client.get(url_for('main.show_accounts_or_dashboard'))
    assert response.status_code == 302
    assert response.location == url_for('main.index', _external=True)


def test_show_accounts_or_dashboard_redirects_to_service_dashboard_if_platform_admin(
    client,
    mocker,
    mock_get_service
):
    client.login(user_with_orgs_and_services(num_orgs=1, num_services=1, platform_admin=True), mocker=mocker)
    with client.session_transaction() as session:
        session['service_id'] = 'service2'
        session['organisation_id'] = None

    response = client.get(url_for('.show_accounts_or_dashboard'))

    assert response.status_code == 302
    assert response.location == url_for(
        'main.service_dashboard',
        service_id='service2',
        _external=True
    )


def test_show_accounts_or_dashboard_redirects_to_org_dashboard_if_platform_admin(
    client,
    mocker
):
    client.login(user_with_orgs_and_services(num_orgs=1, num_services=1, platform_admin=True), mocker=mocker)
    with client.session_transaction() as session:
        session['service_id'] = None
        session['organisation_id'] = 'org2'

    response = client.get(url_for('.show_accounts_or_dashboard'))

    assert response.status_code == 302
    assert response.location == url_for(
        'main.organisation_dashboard',
        org_id='org2',
        _external=True
    )

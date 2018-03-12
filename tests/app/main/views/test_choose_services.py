from bs4 import BeautifulSoup
from flask import url_for


def test_should_show_choose_services_page(
    logged_in_client,
    mock_login,
    mock_get_user,
    api_user_active,
    mock_get_services,
):
    response = logged_in_client.get(url_for('main.choose_service'))

    assert response.status_code == 200
    resp_data = response.get_data(as_text=True)
    assert 'Choose service' in resp_data
    services = mock_get_services.side_effect()
    assert mock_get_services.called
    assert services['data'][0]['name'] in resp_data
    assert services['data'][1]['name'] in resp_data


def test_should_show_choose_services_page_if_no_services(
    logged_in_client,
    mock_login,
    api_user_active,
):
    # if users last service has been archived there'll be no services
    # mock_login already patches get_services to return no data
    response = logged_in_client.get(url_for('main.choose_service'))
    assert response.status_code == 200
    resp_data = response.get_data(as_text=True)
    assert 'Choose service' in resp_data
    assert 'Add a new service' in resp_data


def test_redirect_if_only_one_service(
    logged_in_client,
    mock_login,
    api_user_active,
    mock_get_services_with_one_service,
):
    response = logged_in_client.get(url_for('main.show_all_services_or_dashboard'))

    service = mock_get_services_with_one_service.side_effect()['data'][0]
    assert response.status_code == 302
    assert response.location == url_for('main.service_dashboard', service_id=service['id'], _external=True)


def test_redirect_if_multiple_services(
    logged_in_client,
    mock_login,
    api_user_active,
):
    response = logged_in_client.get(url_for('main.show_all_services_or_dashboard'))

    assert response.status_code == 302
    assert response.location == url_for('main.choose_service', _external=True)


def test_redirect_if_service_in_session(
    logged_in_client,
    mock_login,
    api_user_active,
    mock_get_services,
    mock_get_service,
):
    with logged_in_client.session_transaction() as session:
        session['service_id'] = '147ad62a-2951-4fa1-9ca0-093cd1a52c52'
    response = logged_in_client.get(url_for('main.show_all_services_or_dashboard'))

    assert response.status_code == 302
    assert response.location == url_for(
        'main.service_dashboard',
        service_id='147ad62a-2951-4fa1-9ca0-093cd1a52c52',
        _external=True
    )


def test_dont_redirect_if_wrong_service(
    logged_in_client,
    mock_login,
    api_user_active,
    mock_get_services,
    mock_get_service,
):
    with logged_in_client.session_transaction() as session:
        session['service_id'] = 'nope-nope-nope-nope'
    response = logged_in_client.get(url_for('main.show_all_services_or_dashboard'))

    assert response.status_code == 302
    assert response.location == url_for(
        'main.choose_service',
        _external=True
    )


def test_redirect_to_non_owned_service_if_platform_admin(
    logged_in_platform_admin_client,
    mock_get_services,
    mock_get_service,
):
    with logged_in_platform_admin_client.session_transaction() as session:
        session['service_id'] = 'yes-yes-yes-yes'
    response = logged_in_platform_admin_client.get(url_for('main.show_all_services_or_dashboard'))

    assert response.status_code == 302
    assert response.location == url_for(
        'main.service_dashboard',
        service_id='yes-yes-yes-yes',
        _external=True,
    )


def test_should_redirect_if_not_logged_in(
    logged_in_client,
    app_
):
    response = logged_in_client.get(url_for('main.show_all_services_or_dashboard'))
    assert response.status_code == 302
    assert url_for('main.index', _external=True) in response.location


def test_should_show_back_to_service_link(
    logged_in_client
):
    response = logged_in_client.get(url_for('main.choose_service'))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.select('.navigation-service a')[0]['href'] == (
        url_for('main.show_all_services_or_dashboard')
    )


def test_should_not_show_back_to_service_link_if_no_service_in_session(
    client,
    api_user_active,
    mock_get_user,
    mock_get_services_with_no_services,
):
    client.login(api_user_active)
    response = client.get(url_for('main.choose_service'))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert len(page.select('.navigation-service a')) == 0

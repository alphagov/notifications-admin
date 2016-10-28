from bs4 import BeautifulSoup
from flask import url_for

import app


def test_all_services_should_render_all_services_template(app_,
                                                          platform_admin_user,
                                                          service_one,
                                                          mocker):
    with app_.test_request_context():
        with app_.test_client() as client:
            _login_user(client, mocker, platform_admin_user, service_one)
            mocker.patch('app.service_api_client.get_services', return_value={'data': [service_one]})
            response = client.get(url_for('main.show_all_services'))
            assert response.status_code == 200
            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
            assert page.h1.string.strip() == 'All services'
            assert app.service_api_client.get_services.call_count == 1


def test_all_service_returns_403_when_not_a_platform_admin(app_,
                                                           active_user_with_permissions,
                                                           service_one,
                                                           mocker):
    with app_.test_request_context():
        with app_.test_client() as client:
            _login_user(client, mocker, active_user_with_permissions, service_one)
            response = client.get(url_for('main.show_all_services'))
            assert response.status_code == 403


def test_non_gov_user_cannot_see_add_service_button(client,
                                                    mock_login,
                                                    mock_get_non_govuser,
                                                    api_nongov_user_active):
    client.login(api_nongov_user_active)
    response = client.get(url_for('main.choose_service'))
    assert 'Add a new service' not in response.get_data(as_text=True)
    assert response.status_code == 200


def _login_user(client, mocker, platform_admin_user, service_one):
    mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
    client.login(platform_admin_user)

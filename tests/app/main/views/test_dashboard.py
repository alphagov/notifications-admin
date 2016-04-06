from flask import url_for

from bs4 import BeautifulSoup

from tests import validate_route_permission
from tests.conftest import SERVICE_ONE_ID


def test_should_show_recent_templates_on_dashboard(app_,
                                                   api_user_active,
                                                   mock_get_service,
                                                   mock_get_service_templates,
                                                   mock_get_service_statistics,
                                                   mock_get_template_statistics,
                                                   mock_get_user,
                                                   mock_get_user_by_email,
                                                   mock_login,
                                                   mock_get_jobs,
                                                   mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

        assert response.status_code == 200
        text = response.get_data(as_text=True)
        mock_get_service_statistics.assert_called_once_with(SERVICE_ONE_ID)
        mock_get_template_statistics.assert_called_once_with(SERVICE_ONE_ID)

        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        headers = [header.text.strip() for header in page.find_all('h2')]
        assert 'Test Service' in headers
        assert 'Sent today' in headers
        template_usage_headers = [th.text.strip() for th in page.thead.find_all('th')]
        for th in ['Template', 'Type', 'Date', 'Usage']:
            assert th in template_usage_headers


def _test_dashboard_menu(mocker, app_, usr, service, permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            usr._permissions[str(service['id'])] = permissions
            mocker.patch('app.user_api_client.check_verify_code', return_value=(True, ''))
            mocker.patch('app.service_api_client.get_services', return_value={'data': [service]})
            mocker.patch('app.user_api_client.get_user', return_value=usr)
            mocker.patch('app.user_api_client.get_user_by_email', return_value=usr)
            mocker.patch('app.service_api_client.get_service', return_value={'data': service})
            mocker.patch('app.statistics_api_client.get_statistics_for_service', return_value={'data': [{}]})
            client.login(usr)
            return client.get(url_for('main.service_dashboard', service_id=service['id']))


def test_menu_send_messages(mocker,
                            app_,
                            api_user_active,
                            service_one,
                            mock_get_service_templates,
                            mock_get_jobs,
                            mock_get_template_statistics):

    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            api_user_active,
            service_one,
            ['view_activity', 'send_texts', 'send_emails', 'send_letters'])
        page = resp.get_data(as_text=True)
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='email')in page
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='sms')in page
        assert url_for('main.view_notifications', service_id=service_one['id']) in page
        assert url_for('main.manage_users', service_id=service_one['id']) in page
        assert url_for('main.documentation') in page

        assert url_for('main.service_settings', service_id=service_one['id']) not in page
        assert url_for('main.api_keys', service_id=service_one['id']) not in page
        assert url_for('main.show_all_services') not in page


def test_menu_manage_service(mocker,
                             app_,
                             api_user_active,
                             service_one,
                             mock_get_service_templates,
                             mock_get_jobs,
                             mock_get_template_statistics):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            api_user_active,
            service_one,
            ['view_activity', 'manage_users', 'manage_templates', 'manage_settings'])
        page = resp.get_data(as_text=True)
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='email') in page
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='sms') in page
        assert url_for('main.view_notifications', service_id=service_one['id']) in page
        assert url_for('main.manage_users', service_id=service_one['id']) in page
        assert url_for('main.service_settings', service_id=service_one['id']) in page
        assert url_for('main.documentation') in page

        assert url_for('main.api_keys', service_id=service_one['id']) not in page
        assert url_for('main.show_all_services') not in page


def test_menu_manage_api_keys(mocker,
                              app_,
                              api_user_active,
                              service_one,
                              mock_get_service_templates,
                              mock_get_jobs,
                              mock_get_template_statistics):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            api_user_active,
            service_one,
            ['view_activity', 'manage_api_keys'])
        page = resp.get_data(as_text=True)
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='email') in page
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='sms') in page
        assert url_for('main.view_notifications', service_id=service_one['id']) in page
        assert url_for('main.manage_users', service_id=service_one['id']) in page
        assert url_for('main.service_settings', service_id=service_one['id']) not in page
        assert url_for('main.show_all_services') not in page

        assert url_for('main.api_keys', service_id=service_one['id']) in page


def test_menu_all_services_for_platform_admin_user(mocker,
                                                   app_,
                                                   platform_admin_user,
                                                   service_one,
                                                   mock_get_service_templates,
                                                   mock_get_jobs,
                                                   mock_get_template_statistics):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            platform_admin_user,
            service_one,
            [])
        page = resp.get_data(as_text=True)
        assert url_for('main.show_all_services') in page
        assert url_for('main.choose_template', service_id=service_one['id'], template_type='sms') in page
        assert url_for('main.choose_template', service_id=service_one['id'], template_type='email') in page
        assert url_for('main.manage_users', service_id=service_one['id']) in page
        assert url_for('main.service_settings', service_id=service_one['id']) in page
        assert url_for('main.view_notifications', service_id=service_one['id']) in page
        assert url_for('main.api_keys', service_id=service_one['id']) not in page
        assert url_for('main.edit_service_template', service_id=service_one['id'], template_id=1) in page


def test_route_for_service_permissions(mocker,
                                       app_,
                                       api_user_active,
                                       service_one,
                                       mock_get_service,
                                       mock_get_user,
                                       mock_get_service_templates,
                                       mock_get_jobs,
                                       mock_get_service_statistics,
                                       mock_get_template_statistics):
    routes = [
        'main.service_dashboard']
    with app_.test_request_context():
        # Just test that the user is part of the service
        for route in routes:
            validate_route_permission(
                mocker,
                app_,
                "GET",
                200,
                url_for(
                    route,
                    service_id=service_one['id']),
                ['view_activity'],
                api_user_active,
                service_one)

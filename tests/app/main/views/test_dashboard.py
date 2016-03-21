from flask import url_for, session
from bs4 import BeautifulSoup


def test_should_show_recent_jobs_on_dashboard(app_,
                                              api_user_active,
                                              mock_get_service,
                                              mock_get_service_templates,
                                              mock_get_service_statistics,
                                              mock_get_user,
                                              mock_get_user_by_email,
                                              mock_login,
                                              mock_get_jobs):

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.service_dashboard', service_id=123))

        assert response.status_code == 200
        text = response.get_data(as_text=True)
        assert 'Test Service' in text


def _test_dashboard_menu(mocker, app_, usr, service, permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            usr._permissions[str(service['id'])] = permissions
            mocker.patch(
                'app.user_api_client.check_verify_code',
                return_value=(True, ''))
            mocker.patch(
                'app.notifications_api_client.get_services',
                return_value={'data': []})
            mocker.patch('app.user_api_client.get_user', return_value=usr)
            mocker.patch('app.user_api_client.get_user_by_email', return_value=usr)
            mocker.patch('app.notifications_api_client.get_service', return_value={'data': service})
            mocker.patch('app.statistics_api_client.get_statistics_for_service', return_value={'data': [{}]})
            client.login(usr)
            return client.get(url_for('main.service_dashboard', service_id=service['id']))


def test_menu_send_messages(mocker, app_, api_user_active, service_one, mock_get_service_templates, mock_get_jobs):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            api_user_active,
            service_one,
            ['send_texts', 'send_emails', 'send_letters'])
        page = resp.get_data(as_text=True)
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='email')in page
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='sms')in page

        assert url_for('main.manage_users', service_id=service_one['id']) not in page
        assert url_for('main.service_settings', service_id=service_one['id']) not in page

        assert url_for('main.api_keys', service_id=service_one['id']) not in page
        assert url_for('main.documentation', service_id=service_one['id']) not in page


def test_menu_manage_service(mocker, app_, api_user_active, service_one, mock_get_service_templates, mock_get_jobs):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            api_user_active,
            service_one,
            ['manage_users', 'manage_templates', 'manage_settings'])
        page = resp.get_data(as_text=True)
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='email') in page
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='sms') in page

        assert url_for('main.manage_users', service_id=service_one['id']) in page
        assert url_for('main.service_settings', service_id=service_one['id']) in page

        assert url_for('main.api_keys', service_id=service_one['id']) not in page
        assert url_for('main.documentation', service_id=service_one['id']) not in page


def test_menu_manage_api_keys(mocker, app_, api_user_active, service_one, mock_get_service_templates, mock_get_jobs):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            api_user_active,
            service_one,
            ['manage_api_keys', 'access_developer_docs'])
        page = resp.get_data(as_text=True)
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='email') in page
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_type='sms') in page

        assert url_for('main.manage_users', service_id=service_one['id']) not in page
        assert url_for('main.service_settings', service_id=service_one['id']) not in page

        assert url_for('main.api_keys', service_id=service_one['id']) in page
        assert url_for('main.documentation', service_id=service_one['id']) in page

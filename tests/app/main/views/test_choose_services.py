from flask import url_for


def test_should_show_choose_services_page(app_,
                                          mock_login,
                                          mock_get_user,
                                          api_user_active,
                                          mock_get_services):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.choose_service'))

        assert response.status_code == 200
        resp_data = response.get_data(as_text=True)
        assert 'Choose service' in resp_data
        services = mock_get_services.side_effect()
        assert mock_get_services.called
        assert services['data'][0]['name'] in resp_data
        assert services['data'][1]['name'] in resp_data
        assert 'List all services' not in resp_data


def test_should_show_all_services_for_platform_admin_user(app_,
                                                          platform_admin_user,
                                                          mock_get_services,
                                                          mocker):
    with app_.test_request_context():
        with app_.test_client() as client:
            mocker.patch('app.user_api_client.get_user', return_value=platform_admin_user)
            client.login(platform_admin_user)
        response = client.get(url_for('main.choose_service'))

        assert response.status_code == 200
        resp_data = response.get_data(as_text=True)
        assert 'Choose service' in resp_data
        services = mock_get_services.side_effect()
        assert mock_get_services.called
        assert services['data'][0]['name'] in resp_data
        assert services['data'][1]['name'] in resp_data
        assert 'List all services' in resp_data

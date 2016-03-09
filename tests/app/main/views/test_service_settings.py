from flask import (url_for, session)
from tests import validate_route_permission


def test_should_show_overview(app_,
                              api_user_active,
                              mock_get_service,
                              mock_get_user,
                              mock_get_user_by_email,
                              mock_login,
                              mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = 123
            response = client.get(url_for(
                'main.service_settings', service_id=service_id))
        assert response.status_code == 200
        resp_data = response.get_data(as_text=True)
        assert 'Service settings' in resp_data
        service = mock_get_service.side_effect(service_id)['data']
        assert mock_get_service.called


def test_should_show_service_name(app_,
                                  api_user_active,
                                  mock_get_service,
                                  mock_get_user,
                                  mock_get_user_by_email,
                                  mock_login,
                                  mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = 123
            response = client.get(url_for(
                'main.service_name_change', service_id=service_id))
        assert response.status_code == 200
        resp_data = response.get_data(as_text=True)
        assert 'Change your service name' in resp_data
        assert mock_get_service.called
        service = mock_get_service.side_effect(service_id)['data']


def test_should_redirect_after_change_service_name(app_,
                                                   api_user_active,
                                                   mock_get_service,
                                                   mock_get_user,
                                                   mock_get_user_by_email,
                                                   mock_login,
                                                   mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = 123
            response = client.post(url_for(
                'main.service_name_change', service_id=service_id))

        assert response.status_code == 302
        settings_url = url_for(
            'main.service_name_change_confirm', service_id=service_id, _external=True)
        assert settings_url == response.location
        assert mock_get_service.called


def test_should_show_service_name_confirmation(app_,
                                               api_user_active,
                                               mock_get_service,
                                               mock_get_user,
                                               mock_get_user_by_email,
                                               mock_login,
                                               mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = 123
            response = client.get(url_for(
                'main.service_name_change_confirm', service_id=service_id))

        assert response.status_code == 200
        resp_data = response.get_data(as_text=True)
        assert 'Change your service name' in resp_data
        assert mock_get_service.called


def test_should_redirect_after_service_name_confirmation(app_,
                                                         api_user_active,
                                                         mock_get_service,
                                                         mock_update_service,
                                                         mock_get_user,
                                                         mock_get_user_by_email,
                                                         mock_login,
                                                         mock_verify_password,
                                                         mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = 123
            service_new_name = 'New Name'
            with client.session_transaction() as session:
                session['service_name_change'] = service_new_name
            response = client.post(url_for(
                'main.service_name_change_confirm', service_id=service_id))

        assert response.status_code == 302
        settings_url = url_for(
            'main.service_settings', service_id=service_id, _external=True)
        resp_data = response.get_data(as_text=True)
        assert settings_url == response.location
        assert mock_get_service.called
        assert mock_update_service.called


def test_should_show_request_to_go_live(app_,
                                        api_user_active,
                                        mock_get_service,
                                        mock_get_user,
                                        mock_get_user_by_email,
                                        mock_login,
                                        mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = 123
            response = client.get(
                url_for('main.service_request_to_go_live', service_id=service_id))
        service = mock_get_service.side_effect(service_id)['data']
        assert response.status_code == 200
        resp_data = response.get_data(as_text=True)
        assert 'Request to go live' in resp_data
        assert mock_get_service.called


def test_should_redirect_after_request_to_go_live(app_,
                                                  api_user_active,
                                                  mock_get_service,
                                                  mock_update_service,
                                                  mock_get_user,
                                                  mock_get_user_by_email,
                                                  mock_login,
                                                  mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = 123
            response = client.post(url_for(
                'main.service_request_to_go_live', service_id=service_id))

        assert response.status_code == 302
        settings_url = url_for(
            'main.service_settings', service_id=service_id, _external=True)
        assert settings_url == response.location
        assert mock_get_service.called
        assert mock_update_service.called


def test_should_show_status_page(app_,
                                 api_user_active,
                                 mock_get_service,
                                 mock_get_user,
                                 mock_get_user_by_email,
                                 mock_login,
                                 mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = 123
            response = client.get(url_for(
                'main.service_status_change', service_id=service_id))

        assert response.status_code == 200
        resp_data = response.get_data(as_text=True)
        assert 'Suspend API keys' in resp_data
        assert mock_get_service.called


def test_should_show_redirect_after_status_change(app_,
                                                  api_user_active,
                                                  mock_get_service,
                                                  mock_get_user,
                                                  mock_get_user_by_email,
                                                  mock_login,
                                                  mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = 123
            response = client.post(url_for(
                'main.service_status_change', service_id=service_id))

        assert response.status_code == 302
        redirect_url = url_for(
            'main.service_status_change_confirm', service_id=service_id, _external=True)
        assert redirect_url == response.location
        assert mock_get_service.called


def test_should_show_status_confirmation(app_,
                                         api_user_active,
                                         mock_get_service,
                                         mock_get_user,
                                         mock_get_user_by_email,
                                         mock_login,
                                         mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = 123
            response = client.get(url_for(
                'main.service_status_change_confirm', service_id=service_id))

        assert response.status_code == 200
        resp_data = response.get_data(as_text=True)
        assert 'Turn off all outgoing notifications' in resp_data
        assert mock_get_service.called


def test_should_redirect_after_status_confirmation(app_,
                                                   api_user_active,
                                                   mock_get_service,
                                                   mock_update_service,
                                                   mock_get_user,
                                                   mock_get_user_by_email,
                                                   mock_login,
                                                   mock_verify_password,
                                                   mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = 123
            response = client.post(url_for(
                'main.service_status_change_confirm', service_id=service_id))

        assert response.status_code == 302
        settings_url = url_for(
            'main.service_settings', service_id=service_id, _external=True)
        assert settings_url == response.location
        assert mock_get_service.called
        assert mock_update_service.called


def test_should_show_delete_page(app_,
                                 api_user_active,
                                 mock_get_service,
                                 mock_get_user,
                                 mock_get_user_by_email,
                                 mock_login,
                                 mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = 123
            response = client.get(url_for(
                'main.service_delete', service_id=service_id))

        assert response.status_code == 200
        assert 'Delete this service from GOV.UK Notify' in response.get_data(as_text=True)
        assert mock_get_service.called


def test_should_show_redirect_after_deleting_service(app_,
                                                     api_user_active,
                                                     mock_get_service,
                                                     mock_get_user,
                                                     mock_get_user_by_email,
                                                     mock_login,
                                                     mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = 123
            response = client.post(url_for(
                'main.service_delete', service_id=service_id))

        assert response.status_code == 302
        delete_url = url_for(
            'main.service_delete_confirm', service_id=service_id, _external=True)
        assert delete_url == response.location


def test_should_show_delete_confirmation(app_,
                                         api_user_active,
                                         mock_get_service,
                                         mock_get_user,
                                         mock_get_user_by_email,
                                         mock_login,
                                         mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = 123
            response = client.get(url_for(
                'main.service_delete_confirm', service_id=service_id))

        assert response.status_code == 200
        assert 'Delete this service from Notify' in response.get_data(as_text=True)
        assert mock_get_service.called


def test_should_redirect_delete_confirmation(app_,
                                             api_user_active,
                                             mock_get_service,
                                             mock_delete_service,
                                             mock_get_user,
                                             mock_get_user_by_email,
                                             mock_login,
                                             mock_verify_password,
                                             mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = 123
            response = client.post(url_for(
                'main.service_delete_confirm', service_id=service_id))

        assert response.status_code == 302
        choose_url = url_for(
            'main.choose_service', _external=True)
        assert choose_url == response.location
        assert mock_get_service.called
        assert mock_delete_service.called


def test_route_permissions(mocker, app_, api_user_active, service_one):
    routes = [
        'main.service_settings',
        'main.service_name_change',
        'main.service_name_change_confirm',
        'main.service_request_to_go_live',
        'main.service_status_change',
        'main.service_status_change_confirm',
        'main.service_delete',
        'main.service_delete_confirm']
    with app_.test_request_context():
        for route in routes:
            validate_route_permission(
                mocker,
                app_,
                "GET",
                200,
                url_for(route, service_id=service_one['id']),
                ['manage_settings'],
                api_user_active,
                service_one)


def test_route_invalid_permissions(mocker, app_, api_user_active, service_one):
    routes = [
        'main.service_settings',
        'main.service_name_change',
        'main.service_name_change_confirm',
        'main.service_request_to_go_live',
        'main.service_status_change',
        'main.service_status_change_confirm',
        'main.service_delete',
        'main.service_delete_confirm']
    with app_.test_request_context():
        for route in routes:
            validate_route_permission(
                mocker,
                app_,
                "GET",
                403,
                url_for(route, service_id=service_one['id']),
                ['blah'],
                api_user_active,
                service_one)

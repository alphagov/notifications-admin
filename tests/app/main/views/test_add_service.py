from flask import url_for


def test_get_should_render_add_service_template(app_,
                                                api_user_active,
                                                mocker):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active, mocker)
            response = client.get(url_for('main.add_service'))
            assert response.status_code == 200
            assert 'Which service do you want to set up notifications for?' in response.get_data(as_text=True)


def test_should_add_service_and_redirect_to_next_page(app_,
                                                      mocker,
                                                      mock_create_service,
                                                      mock_get_services,
                                                      api_user_active):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active, mocker)
            response = client.post(
                url_for('main.add_service'),
                data={'name': 'testing the post'})
            assert response.status_code == 302
            assert response.location == url_for('main.service_dashboard', service_id=101, _external=True)
            assert mock_get_services.called
            mock_create_service.asset_called_once_with('testing the post', False,
                                                       app_.config['DEFAULT_SERVICE_LIMIT'],
                                                       True, api_user_active.id)


def test_should_return_form_errors_when_service_name_is_empty(app_,
                                                              mocker,
                                                              api_user_active):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active, mocker)
            response = client.post(url_for('main.add_service'), data={})
            assert response.status_code == 200
            assert 'Service name can’t be empty' in response.get_data(as_text=True)


def test_should_return_form_errors_with_duplicate_service_name_regardless_of_case(app_,
                                                                                  mocker,
                                                                                  service_one,
                                                                                  mock_get_services,
                                                                                  api_user_active,
                                                                                  mock_create_service):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active, mocker, service_one)
            response = client.post(url_for('main.add_service'), data={'name': 'SERVICE_TWO'})

            assert response.status_code == 200
            assert 'This service name is already in use' in response.get_data(as_text=True)
            assert mock_get_services.called
            assert not mock_create_service.called

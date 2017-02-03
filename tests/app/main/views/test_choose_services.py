from flask import url_for


def test_should_show_choose_services_page(
    app_,
    mock_login,
    mock_get_user,
    api_user_active,
    mock_get_services,
):
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


def test_should_show_choose_services_page_if_no_services(
    client,
    mock_login,
    api_user_active,
):
    # if users last service has been archived there'll be no services
    # mock_login already patches get_services to return no data
    client.login(api_user_active)
    response = client.get(url_for('main.choose_service'))
    assert response.status_code == 200
    resp_data = response.get_data(as_text=True)
    assert 'Choose service' in resp_data
    assert 'Add a new service' in resp_data


def test_redirect_if_only_one_service(
    app_,
    mock_login,
    api_user_active,
    mock_get_services_with_one_service,
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.show_all_services_or_dashboard'))

        service = mock_get_services_with_one_service.side_effect()['data'][0]
        assert response.status_code == 302
        assert response.location == url_for('main.service_dashboard', service_id=service['id'], _external=True)


def test_redirect_if_multiple_services(
    app_,
    mock_login,
    api_user_active,
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.show_all_services_or_dashboard'))

        assert response.status_code == 302
        assert response.location == url_for('main.choose_service', _external=True)


def test_redirect_if_service_in_session(
    app_,
    mock_login,
    api_user_active,
    mock_get_services,
    mock_get_service,
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            with client.session_transaction() as session:
                session['service_id'] = '147ad62a-2951-4fa1-9ca0-093cd1a52c52'
            response = client.get(url_for('main.show_all_services_or_dashboard'))

        assert response.status_code == 302
        assert response.location == url_for(
            'main.service_dashboard',
            service_id='147ad62a-2951-4fa1-9ca0-093cd1a52c52',
            _external=True
        )


def test_should_redirect_if_not_logged_in(
    app_
):
    with app_.test_request_context():
        with app_.test_client() as client:
            response = client.get(url_for('main.show_all_services_or_dashboard'))
            assert response.status_code == 302
            assert url_for('main.index', _external=True) in response.location

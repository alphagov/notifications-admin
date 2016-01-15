from tests.app.main import create_test_user


def test_should_show_overview(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/services/123/service-settings')
        assert response.status_code == 200
        assert 'Service settings' in response.get_data(as_text=True)


def test_should_show_service_name(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/services/123/service-settings/name')
        assert response.status_code == 200
        assert 'Change your service name' in response.get_data(as_text=True)


def test_should_redirect_after_change_service_name(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.post('/services/123/service-settings/request-to-go-live')

    assert response.status_code == 302
    assert 'http://localhost/services/123/service-settings' == response.location


def test_should_show_service_name_confirmation(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/services/123/service-settings/name/confirm')

    assert response.status_code == 200
    assert 'Change your service name' in response.get_data(as_text=True)


def test_should_redirect_after_service_name_confirmation(app_, db_,
                                                         db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.post('/services/123/service-settings/name/confirm')

    assert response.status_code == 302
    assert 'http://localhost/services/123/service-settings' == response.location


def test_should_show_request_to_go_live(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/services/123/service-settings/request-to-go-live')

    assert response.status_code == 200
    assert 'Request to go live' in response.get_data(as_text=True)


def test_should_redirect_after_request_to_go_live(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.post('/services/123/service-settings/request-to-go-live')

    assert response.status_code == 302
    assert 'http://localhost/services/123/service-settings' == response.location


def test_should_show_status_page(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/services/123/service-settings/status')

    assert response.status_code == 200
    assert 'Turn off all outgoing notifications' in response.get_data(as_text=True)


def test_should_show_redirect_after_status_change(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.post('/services/123/service-settings/status')

    assert response.status_code == 302
    assert 'http://localhost/services/123/service-settings/status/confirm' == response.location


def test_should_show_status_confirmation(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/services/123/service-settings/status/confirm')

    assert response.status_code == 200
    assert 'Turn off all outgoing notifications' in response.get_data(as_text=True)


def test_should_redirect_after_status_confirmation(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.post('/services/123/service-settings/status/confirm')

    assert response.status_code == 302
    assert 'http://localhost/services/123/service-settings' == response.location


def test_should_show_delete_page(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/services/123/service-settings/delete')

    assert response.status_code == 200
    assert 'Delete this service from Notify' in response.get_data(as_text=True)


def test_should_show_redirect_after_deleting_service(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.post('/services/123/service-settings/delete')

    assert response.status_code == 302
    assert 'http://localhost/services/123/service-settings/delete/confirm' == response.location


def test_should_show_delete_confirmation(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/services/123/service-settings/delete/confirm')

    assert response.status_code == 200
    assert 'Delete this service from Notify' in response.get_data(as_text=True)


def test_should_redirect_delete_confirmation(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.post('/services/123/service-settings/delete/confirm')

    assert response.status_code == 302
    assert 'http://localhost/services/123/dashboard' == response.location

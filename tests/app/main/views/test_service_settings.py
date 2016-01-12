from tests.app.main import create_test_user


def test_should_show_overview(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/service-settings')
        assert response.status_code == 200
        assert 'Service settings' in response.get_data(as_text=True)


def test_should_show_service_name(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/service-settings/name')
        assert response.status_code == 200
        assert 'Change your service name' in response.get_data(as_text=True)


def test_should_redirect_after_change_service_name(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.post('/service-settings/request-to-go-live')

    assert response.status_code == 302
    assert 'http://localhost/service-settings' == response.location


def test_should_show_service_name_confirmation(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/service-settings/name/confirm')

    assert response.status_code == 200
    assert 'Change your service name' in response.get_data(as_text=True)


def test_should_redirect_after_service_name_confirmation(notifications_admin, notifications_admin_db,
                                                         notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.post('/service-settings/name/confirm')

    assert response.status_code == 302
    assert 'http://localhost/service-settings' == response.location


def test_should_show_request_to_go_live(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/service-settings/request-to-go-live')

    assert response.status_code == 200
    assert 'Request to go live' in response.get_data(as_text=True)


def test_should_redirect_after_request_to_go_live(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.post('/service-settings/request-to-go-live')

    assert response.status_code == 302
    assert 'http://localhost/service-settings' == response.location


def test_should_show_status_page(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/service-settings/status')

    assert response.status_code == 200
    assert 'Turn off all outgoing notifications' in response.get_data(as_text=True)


def test_should_show_redirect_after_status_change(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.post('/service-settings/status')

    assert response.status_code == 302
    assert 'http://localhost/service-settings/status/confirm' == response.location


def test_should_show_status_confirmation(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/service-settings/status/confirm')

    assert response.status_code == 200
    assert 'Turn off all outgoing notifications' in response.get_data(as_text=True)


def test_should_redirect_after_status_confirmation(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.post('/service-settings/status/confirm')

    assert response.status_code == 302
    assert 'http://localhost/service-settings' == response.location


def test_should_show_delete_page(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/service-settings/delete')

    assert response.status_code == 200
    assert 'Delete this service from Notify' in response.get_data(as_text=True)


def test_should_show_redirect_after_deleting_service(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.post('/service-settings/delete')

    assert response.status_code == 302
    assert 'http://localhost/service-settings/delete/confirm' == response.location


def test_should_show_delete_confirmation(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/service-settings/delete/confirm')

    assert response.status_code == 200
    assert 'Delete this service from Notify' in response.get_data(as_text=True)


def test_should_redirect_delete_confirmation(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.post('/service-settings/delete/confirm')

    assert response.status_code == 302
    assert 'http://localhost/dashboard' == response.location

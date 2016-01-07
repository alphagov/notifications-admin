def test_should_show_overview(notifications_admin):
    response = notifications_admin.test_client().get('/service-settings')

    assert response.status_code == 200
    assert 'Service settings' in response.get_data(as_text=True)


def test_should_show_service_name(notifications_admin):
    response = notifications_admin.test_client().get('/service-settings/name')

    assert response.status_code == 200
    assert 'Service name' in response.get_data(as_text=True)


def test_should_redirect_after_change_service_name(notifications_admin):
    response = notifications_admin.test_client().post('/service-settings/request-to-go-live')

    assert response.status_code == 302
    assert 'http://localhost/service-settings' == response.location


def test_should_show_request_to_go_live(notifications_admin):
    response = notifications_admin.test_client().get('/service-settings/request-to-go-live')

    assert response.status_code == 200
    assert 'Request to go live' in response.get_data(as_text=True)


def test_should_redirect_after_request_to_go_live(notifications_admin):
    response = notifications_admin.test_client().post('/service-settings/request-to-go-live')

    assert response.status_code == 302
    assert 'http://localhost/service-settings' == response.location


def test_should_show_status_page(notifications_admin):
    response = notifications_admin.test_client().get('/service-settings/status')

    assert response.status_code == 200
    assert 'Suspend your service' in response.get_data(as_text=True)


def test_should_show_redirect_after_status_change(notifications_admin):
    response = notifications_admin.test_client().post('/service-settings/status')

    assert response.status_code == 302
    assert 'http://localhost/service-settings' == response.location


def test_should_show_delete_page(notifications_admin):
    response = notifications_admin.test_client().get('/service-settings/delete')

    assert response.status_code == 200
    assert 'Delete service' in response.get_data(as_text=True)


def test_should_show_redirect_after_deleting_service(notifications_admin):
    response = notifications_admin.test_client().post('/service-settings/delete')

    assert response.status_code == 302
    assert 'http://localhost/' == response.location

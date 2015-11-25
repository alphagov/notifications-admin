def test_index_returns_200(notifications_admin):
    response = notifications_admin.test_client().get('/index')
    assert response.status_code == 200
    assert response.data.decode('utf-8') == 'Hello from notifications-admin'


def test_helloworld_returns_200(notifications_admin):
    response = notifications_admin.test_client().get('/helloworld')
    assert response.status_code == 200
    assert 'Hello world!' in response.data.decode('utf-8')

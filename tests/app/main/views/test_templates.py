from tests.app.main import create_test_user


def test_should_return_list_of_all_templates(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/services/123/templates')

    assert response.status_code == 200


def test_should_show_page_for_one_templates(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/services/123/templates/template')

    assert response.status_code == 200


def test_should_redirect_when_saving_a_template(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.post('/services/123/templates/template')

    assert response.status_code == 302
    assert response.location == 'http://localhost/services/123/templates'

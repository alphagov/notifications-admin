from tests.app.main import create_test_user


def test_should_return_list_of_all_templates(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/services/123/templates')

    assert response.status_code == 200


def test_should_show_page_for_one_templates(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/services/123/templates/template')

    assert response.status_code == 200


def test_should_redirect_when_saving_a_template(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.post('/services/123/templates/template')

    assert response.status_code == 302
    assert response.location == 'http://localhost/services/123/templates'

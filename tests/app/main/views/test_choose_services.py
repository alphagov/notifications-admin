from tests.app.main import create_test_user
from flask import url_for


def test_should_show_choose_services_page(notifications_admin,
                                          notifications_admin_db,
                                          notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/services')

        assert response.status_code == 200
        assert 'Choose service' in response.get_data(as_text=True)

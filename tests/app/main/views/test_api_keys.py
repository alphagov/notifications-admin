from tests.app.main import create_test_user
from flask import url_for


def test_should_show_api_keys_and_documentation_page(notifications_admin,
                                                     notifications_admin_db,
                                                     notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get(url_for('.api_keys', service_id=123))

        assert response.status_code == 200

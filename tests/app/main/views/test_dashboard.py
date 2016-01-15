from tests.app.main import create_test_user
from flask import url_for


def test_should_show_recent_jobs_on_dashboard(app_,
                                              db_,
                                              db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/services/123/dashboard')

        assert response.status_code == 200
        assert 'Test message 1' in response.get_data(as_text=True)
        assert 'Asdfgg' in response.get_data(as_text=True)

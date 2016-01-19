from app.models import User
from flask import url_for


def test_should_show_recent_jobs_on_dashboard(app_,
                                              db_,
                                              db_session,
                                              active_user,
                                              mock_get_service):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user)
            response = client.get(url_for('main.service_dashboard', service_id=123))

        assert response.status_code == 200
        assert 'Test message 1' in response.get_data(as_text=True)
        assert 'Asdfgg' in response.get_data(as_text=True)

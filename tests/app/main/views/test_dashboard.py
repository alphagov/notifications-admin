from flask import url_for, session


def test_should_show_recent_jobs_on_dashboard(app_,
                                              api_user_active,
                                              mock_get_service,
                                              mock_get_service_templates,
                                              mock_get_user,
                                              mock_get_user_by_email,
                                              mock_login):

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.service_dashboard', service_id=123))

        assert response.status_code == 200
        text = response.get_data(as_text=True)
        assert 'Test Service' in text

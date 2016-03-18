from flask import url_for


def test_render_sign_out_redirects_to_sign_in(app_):
    with app_.test_request_context():
        response = app_.test_client().get(
            url_for('main.sign_out'))
        assert response.status_code == 302
        assert response.location == url_for(
            'main.sign_in', _external=True)


def test_sign_out_user(app_,
                       mock_get_service,
                       api_user_active,
                       mock_get_user,
                       mock_get_user_by_email,
                       mock_get_service_templates,
                       mock_get_service_statistics,
                       mock_login,
                       mock_get_jobs):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            with client.session_transaction() as session:
                assert session.get('user_id') is not None
            # Check we are logged in
            response = client.get(
                url_for('main.service_dashboard', service_id="123"))
            assert response.status_code == 200
            response = client.get(url_for('main.sign_out'))
            assert response.status_code == 302
            assert response.location == url_for(
                'main.sign_in', _external=True)
            with client.session_transaction() as session:
                assert session.get('user_id') is None

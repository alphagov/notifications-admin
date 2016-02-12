from flask import url_for


def test_render_sign_out_redirects_to_sign_in(app_):
    with app_.test_request_context():
        response = app_.test_client().get(
            url_for('main.sign_out'))
        assert response.status_code == 302
        assert response.location == url_for(
            'main.sign_in', _external=True, next=url_for('main.sign_out'))


def test_sign_out_user(app_,
                       mock_get_service,
                       api_user_active,
                       mock_get_user,
                       mock_get_user_by_email,
                       mock_get_service_templates,
                       mock_login,
                       mock_get_jobs):
    with app_.test_request_context():
        email = 'valid@example.gov.uk'
        password = 'val1dPassw0rd!'
        with app_.test_client() as client:
            with client.session_transaction() as session:
                print('session: {}'.format(session))
            client.login(api_user_active)
            # Check we are logged in
            response = client.get(
                url_for('main.service_dashboard', service_id="123"))
            assert response.status_code == 200
            response = client.get(url_for('main.sign_out'))
            assert response.status_code == 302
            assert response.location == url_for(
                'main.index', _external=True)
            assert session.get('ItsdangerousSession') is None

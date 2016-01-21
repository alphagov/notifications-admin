from flask import url_for


def test_should_show_api_keys_and_documentation_page(app_,
                                                     db_,
                                                     db_session,
                                                     mock_api_user,
                                                     mock_user_loader,
                                                     mock_user_dao_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(mock_api_user)
            response = client.get(url_for('main.api_keys', service_id=123))

        assert response.status_code == 200

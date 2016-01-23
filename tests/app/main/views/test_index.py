from flask import url_for


def test_logged_in_user_redirects_to_choose_service(app_,
                                                    db_,
                                                    db_session,
                                                    mock_active_user,
                                                    mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(mock_active_user)
            response = client.get(url_for('main.index'))
            assert response.status_code == 302

            response = client.get(url_for('main.sign_in', follow_redirects=True))
            assert response.location == url_for('main.choose_service', _external=True)

from flask import url_for


def test_should_show_documentation_page(app_,
                                        db_,
                                        db_session,
                                        active_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user)
            response = client.get(url_for('main.documentation', service_id=123))

        assert response.status_code == 200


def test_should_show_api_keys_page(app_,
                                   db_,
                                   db_session,
                                   active_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user)
            response = client.get(url_for('main.api_keys', service_id=123))

        assert response.status_code == 200


def test_should_show_name_api_key_page(app_,
                                       db_,
                                       db_session,
                                       active_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user)
            response = client.get(url_for('main.create_api_key', service_id=123))

        assert response.status_code == 200


def test_should_redirect_to_new_api_key(app_,
                                        db_,
                                        db_session,
                                        active_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user)
            response = client.post(url_for('main.create_api_key', service_id=123))

        assert response.status_code == 302
        assert response.location == url_for('main.show_api_key', service_id=123, _external=True)


def test_should_show_new_api_key(app_,
                                 db_,
                                 db_session,
                                 active_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user)
            response = client.get(url_for('main.show_api_key', service_id=123))

        assert response.status_code == 200


def test_should_show_confirm_revoke_api_key(app_,
                                            db_,
                                            db_session,
                                            active_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user)
            response = client.get(url_for('main.revoke_api_key', service_id=123, key_id=321))

        assert response.status_code == 200


def test_should_redirect_after_revoking_api_key(app_,
                                                db_,
                                                db_session,
                                                active_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user)
            response = client.post(url_for('main.revoke_api_key', service_id=123, key_id=321))

        assert response.status_code == 302
        assert response.location == url_for('.api_keys', service_id=123, _external=True)

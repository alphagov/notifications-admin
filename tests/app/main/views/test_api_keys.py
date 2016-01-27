from datetime import date
from flask import url_for


def test_should_show_api_keys_and_documentation_page(app_,
                                                     api_user_active,
                                                     mock_user_loader,
                                                     mock_user_dao_get_by_email,
                                                     mock_login):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.documentation', service_id=123))

        assert response.status_code == 200


def test_should_show_empty_api_keys_page(app_,
                                         api_user_active,
                                         mock_user_loader,
                                         mock_user_dao_get_by_email,
                                         mock_get_no_api_keys,
                                         mock_login):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.api_keys', service_id=123))

        assert response.status_code == 200
        assert 'You haven’t created any API keys yet' in response.get_data(as_text=True)
        assert 'Create a new API key' in response.get_data(as_text=True)
        mock_get_no_api_keys.assert_called_once_with(service_id=123)


def test_should_show_api_keys_page(app_,
                                   api_user_active,
                                   mock_user_loader,
                                   mock_user_dao_get_by_email,
                                   mock_get_api_keys,
                                   mock_login):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.api_keys', service_id=123))

        assert response.status_code == 200
        assert 'some key name' in response.get_data(as_text=True)
        assert 'another key name' in response.get_data(as_text=True)
        assert 'Revoked Thursday 01 January 1970 at 00:00' in response.get_data(as_text=True)
        mock_get_api_keys.assert_called_once_with(service_id=123)


def test_should_show_name_api_key_page(app_,
                                       api_user_active,
                                       mock_user_loader,
                                       mock_user_dao_get_by_email,
                                       mock_get_api_keys,
                                       mock_login):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.create_api_key', service_id=123))

        assert response.status_code == 200


def test_should_render_show_api_key(app_,
                                    api_user_active,
                                    mock_user_loader,
                                    mock_user_dao_get_by_email,
                                    mock_create_api_key,
                                    mock_get_api_keys,
                                    mock_login):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.post(url_for('main.create_api_key', service_id=123),
                                   data={'key_name': 'some default key name'})

        assert response.status_code == 200
        assert 'some default key name' in response.get_data(as_text=True)
        mock_create_api_key.assert_called_once_with(service_id=123, key_name='some default key name')


def test_should_show_confirm_revoke_api_key(app_,
                                            api_user_active,
                                            mock_user_loader,
                                            mock_user_dao_get_by_email,
                                            mock_get_api_keys,
                                            mock_login):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.revoke_api_key', service_id=123, key_id=321))

        assert response.status_code == 200
        assert 'some key name' in response.get_data(as_text=True)
        mock_get_api_keys.assert_called_once_with(service_id=123, key_id=321)


def test_should_redirect_after_revoking_api_key(app_,
                                                api_user_active,
                                                mock_user_loader,
                                                mock_user_dao_get_by_email,
                                                mock_revoke_api_key,
                                                mock_get_api_keys,
                                                mock_login):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.post(url_for('main.revoke_api_key', service_id=123, key_id=321))

        assert response.status_code == 302
        assert response.location == url_for('.api_keys', service_id=123, _external=True)
        mock_revoke_api_key.assert_called_once_with(service_id=123, key_id=321)
        mock_get_api_keys.assert_called_once_with(service_id=123, key_id=321)

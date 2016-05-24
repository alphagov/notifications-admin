from flask import url_for

from tests.conftest import mock_get_user


def test_should_redirect_if_not_logged_in(app_):
    with app_.test_request_context():
        with app_.test_client() as client:
            response = client.get(url_for('main.platform_admin'))
            assert response.status_code == 302
            assert url_for('main.index', _external=True) in response.location


def test_should_403_if_not_platform_admin(app_, active_user_with_permissions, mocker):
    with app_.test_request_context():
        with app_.test_client() as client:
            mock_get_user(mocker, user=active_user_with_permissions)
            client.login(active_user_with_permissions)

            response = client.get(url_for('main.platform_admin'))

            assert response.status_code == 403


def test_should_render_platform_admin_page(app_, platform_admin_user, mocker):
    with app_.test_request_context():
        with app_.test_client() as client:
            mock_get_user(mocker, user=platform_admin_user)
            client.login(platform_admin_user)
            response = client.get(url_for('main.platform_admin'))

            assert response.status_code == 200
            resp_data = response.get_data(as_text=True)
            assert 'Platform admin' in resp_data

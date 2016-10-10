import pytest
from flask import url_for


def test_logged_in_user_redirects_to_choose_service(app_,
                                                    api_user_active,
                                                    mock_get_user,
                                                    mock_get_user_by_email,
                                                    mock_login):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.index'))
            assert response.status_code == 302

            response = client.get(url_for('main.sign_in', follow_redirects=True))
            assert response.location == url_for('main.choose_service', _external=True)


@pytest.mark.parametrize('view', [
    'cookies', 'trial_mode', 'pricing', 'terms', 'delivery_and_failure'
])
def test_static_pages(app_, view):
    with app_.test_request_context(), app_.test_client() as client:
        response = client.get(url_for('main.{}'.format(view)))
        assert response.status_code == 200

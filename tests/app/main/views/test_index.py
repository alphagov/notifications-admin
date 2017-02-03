import pytest
from flask import url_for


def test_logged_in_user_redirects_to_choose_service(
    logged_in_client,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_login,
):
    response = logged_in_client.get(url_for('main.index'))
    assert response.status_code == 302

    response = logged_in_client.get(url_for('main.sign_in', follow_redirects=True))
    assert response.location == url_for('main.choose_service', _external=True)


@pytest.mark.parametrize('view', [
    'cookies', 'trial_mode', 'pricing', 'terms', 'delivery_and_failure', 'integration_testing'
])
def test_static_pages(
    client,
    view,
):
    response = client.get(url_for('main.{}'.format(view)))
    assert response.status_code == 200

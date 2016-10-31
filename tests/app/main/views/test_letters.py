import pytest
from flask import url_for

from tests import service_json


@pytest.mark.parametrize('can_send_letters, response_code', [
    (True, 200),
    (False, 403)
])
def test_letters_access_restricted(logged_in_client, mocker, can_send_letters, response_code):
    service = service_json(can_send_letters=can_send_letters)
    mocker.patch('app.service_api_client.get_service', return_value={"data": service})

    response = logged_in_client.get(url_for('main.letters', service_id=service['id']))

    assert response.status_code == response_code


def test_letters_lets_in_without_permission(
    client,
    mocker,
    mock_login,
    mock_has_permissions,
    api_user_active,
):
    service = service_json(can_send_letters=True)
    mocker.patch('app.service_api_client.get_service', return_value={"data": service})

    client.login(api_user_active)
    response = client.get(url_for('main.letters', service_id=service['id']))

    assert api_user_active.permissions == {}
    assert response.status_code == 200

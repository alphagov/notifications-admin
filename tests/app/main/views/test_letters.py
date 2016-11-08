import pytest
from flask import url_for
from functools import partial

from tests import service_json

letters_urls = [
    partial(url_for, 'main.choose_template', template_type='letter'),
    partial(url_for, 'main.add_service_template', template_type='letter'),
]


@pytest.mark.parametrize('url', letters_urls)
@pytest.mark.parametrize('can_send_letters, response_code', [
    (True, 200),
    (False, 403)
])
def test_letters_access_restricted(
    logged_in_client,
    mocker,
    can_send_letters,
    response_code,
    mock_get_service_templates,
    url
):
    service = service_json(can_send_letters=can_send_letters)
    mocker.patch('app.service_api_client.get_service', return_value={"data": service})

    response = logged_in_client.get(url(service_id=service['id']))

    assert response.status_code == response_code


@pytest.mark.parametrize('url', letters_urls)
def test_letters_lets_in_without_permission(
    client,
    mocker,
    mock_login,
    mock_has_permissions,
    api_user_active,
    mock_get_service_templates,
    url
):
    service = service_json(can_send_letters=True)
    mocker.patch('app.service_api_client.get_service', return_value={"data": service})

    client.login(api_user_active)
    response = client.get(url(service_id=service['id']))

    assert api_user_active.permissions == {}
    assert response.status_code == 200

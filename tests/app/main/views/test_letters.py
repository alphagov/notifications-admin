import pytest
from bs4 import BeautifulSoup
from flask import url_for
from functools import partial

from tests import service_json

letters_urls = [
    partial(url_for, 'main.add_service_template', template_type='letter'),
]


@pytest.mark.parametrize('url', letters_urls)
@pytest.mark.parametrize('can_send_letters, response_code', [
    (True, 200),
    (False, 403)
])
def test_letters_access_restricted(
    logged_in_platform_admin_client,
    mocker,
    can_send_letters,
    response_code,
    mock_get_service_templates,
    url,
):
    service = service_json(can_send_letters=can_send_letters)
    mocker.patch('app.service_api_client.get_service', return_value={"data": service})

    response = logged_in_platform_admin_client.get(url(service_id=service['id']))

    assert response.status_code == response_code


@pytest.mark.parametrize('url', letters_urls)
def test_letters_lets_in_without_permission(
    client,
    mocker,
    mock_login,
    mock_has_permissions,
    api_user_active,
    mock_get_service_templates,
    url,
):
    service = service_json(can_send_letters=True)
    mocker.patch('app.service_api_client.get_service', return_value={"data": service})

    client.login(api_user_active)
    response = client.get(url(service_id=service['id']))

    assert api_user_active.permissions == {}
    assert response.status_code == 200


@pytest.mark.parametrize('can_send_letters, choices', [
    (True, ['Email', 'Text message', 'Letter']),
    (False, ['Email', 'Text message'])
])
def test_given_option_to_add_letters_if_allowed(
    logged_in_client,
    service_one,
    mocker,
    can_send_letters,
    choices,
):
    service_one['can_send_letters'] = can_send_letters
    mocker.patch('app.service_api_client.get_service', return_value={"data": service_one})

    response = logged_in_client.get(url_for('main.add_template_by_type', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    radios = page.select('input[type=radio]')

    assert len(radios) == len(choices)

    for index, choice in enumerate(choices):
        assert radios[index].text.strip() == choice

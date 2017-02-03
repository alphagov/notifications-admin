from flask import url_for
from bs4 import BeautifulSoup

from tests import service_json


def test_can_see_letters_if_allowed(logged_in_client, mocker):
    service = service_json(can_send_letters=True)
    mocker.patch('app.service_api_client.get_service', return_value={"data": service})

    response = logged_in_client.get(url_for('main.service_settings', service_id=service['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Letter templates' in page.find('nav', class_='navigation').text


def test_cant_see_letters_if_not_allowed(logged_in_client, mocker):
    service = service_json(can_send_letters=False)
    mocker.patch('app.service_api_client.get_service', return_value={"data": service})

    response = logged_in_client.get(url_for('main.service_settings', service_id=service['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Letter templates' not in page.find('nav', class_='navigation').text


def test_can_see_letters_without_permissions(
    client,
    mocker,
    mock_login,
    mock_has_permissions,
    api_user_active,
):
    service = service_json(can_send_letters=True)
    mocker.patch('app.service_api_client.get_service', return_value={"data": service})

    client.login(api_user_active)
    response = client.get(url_for('main.service_settings', service_id=service['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Letter templates' in page.find('nav', class_='navigation').text

from flask import url_for
from bs4 import BeautifulSoup

from tests.conftest import mock_get_user


def test_can_see_letters_if_allowed(
    logged_in_client,
    service_one,
    mocker,
    mock_get_users_by_service,
    mock_get_invites_for_service
):
    service_one['can_send_letters'] = True
    mocker.patch('app.service_api_client.get_service', return_value={"data": service_one})

    response = logged_in_client.get(url_for('main.manage_users', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Letter templates' in page.find('nav', class_='navigation').text


def test_cant_see_letters_if_not_allowed(
    logged_in_client,
    service_one,
    mocker,
    mock_get_users_by_service,
    mock_get_invites_for_service
):
    service_one['can_send_letters'] = False
    mocker.patch('app.service_api_client.get_service', return_value={"data": service_one})

    response = logged_in_client.get(url_for('main.manage_users', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Letter templates' not in page.find('nav', class_='navigation').text


def test_can_see_letters_without_edit_permissions(
    client,
    mocker,
    active_user_view_permissions,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    service_one
):
    mock_get_user(mocker, user=active_user_view_permissions)
    service_one['can_send_letters'] = True
    mocker.patch('app.service_api_client.get_service', return_value={"data": service_one})

    client.login(active_user_view_permissions)
    response = client.get(url_for('main.manage_users', service_id=service_one['id']))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Letter templates' in page.find('nav', class_='navigation').text

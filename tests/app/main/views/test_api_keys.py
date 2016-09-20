import uuid

from collections import OrderedDict
from flask import url_for
from bs4 import BeautifulSoup

from tests import validate_route_permission


def test_should_show_api_page(
    app_,
    mock_login,
    api_user_active,
    mock_get_service,
    mock_has_permissions
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(api_user_active)
        response = client.get(url_for('main.api_integration', service_id=str(uuid.uuid4())))
        assert response.status_code == 200
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.h1.string.strip() == 'API integration'
        assert 'Your service is in trial mode' in page.find('div', {'class': 'banner-warning'}).text


def test_should_show_api_page_for_live_service(
    app_,
    mock_login,
    api_user_active,
    mock_get_live_service,
    mock_has_permissions
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(api_user_active)
        response = client.get(url_for('main.api_integration', service_id=str(uuid.uuid4())))
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert 'Your service is in trial mode' not in page.find('main').text


def test_should_show_api_documentation_page(
    app_,
    mock_login,
    api_user_active,
    mock_get_service,
    mock_has_permissions
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(api_user_active)
        response = client.get(url_for('main.api_documentation', service_id=str(uuid.uuid4())))
        assert response.status_code == 200
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.h1.string.strip() == 'Documentation'


def test_should_show_empty_api_keys_page(app_,
                                         api_user_pending,
                                         mock_login,
                                         mock_get_no_api_keys,
                                         mock_get_service,
                                         mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_pending)
            service_id = str(uuid.uuid4())
            response = client.get(url_for('main.api_keys', service_id=service_id))

        assert response.status_code == 200
        assert 'You haven’t created any API keys yet' in response.get_data(as_text=True)
        assert 'Create an API key' in response.get_data(as_text=True)
        mock_get_no_api_keys.assert_called_once_with(service_id=service_id)


def test_should_show_api_keys_page(app_,
                                   api_user_active,
                                   mock_login,
                                   mock_get_api_keys,
                                   mock_get_service,
                                   mock_has_permissions,
                                   fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.api_keys', service_id=fake_uuid))

        assert response.status_code == 200
        resp_data = response.get_data(as_text=True)
        assert 'some key name' in resp_data
        assert 'another key name' in resp_data
        assert 'Revoked 1 January at 1:00am' in resp_data
        mock_get_api_keys.assert_called_once_with(service_id=fake_uuid)


def test_should_show_create_api_key_page(app_,
                                         api_user_active,
                                         mock_login,
                                         mock_get_api_keys,
                                         mock_get_service,
                                         mock_has_permissions,
                                         fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = fake_uuid
            response = client.get(url_for('main.create_api_key', service_id=fake_uuid))

        assert response.status_code == 200


def test_should_create_api_key_with_type_normal(app_,
                                                api_user_active,
                                                mock_login,
                                                mock_get_api_keys,
                                                mock_get_service,
                                                mock_has_permissions,
                                                fake_uuid,
                                                mocker):
    post = mocker.patch('app.notify_client.api_key_api_client.ApiKeyApiClient.post', return_value={'data': fake_uuid})
    service_id = str(uuid.uuid4())

    with app_.test_request_context(), app_.test_client() as client:
        client.login(api_user_active)
        response = client.post(
            url_for('main.create_api_key', service_id=service_id),
            data={
                'key_name': 'some default key name',
                'key_type': 'normal'
            }
        )

    assert response.status_code == 200
    assert 'some default key name' in response.get_data(as_text=True)
    post.assert_called_once_with(url='/service/{}/api-key'.format(service_id), data={
        'name': 'some default key name',
        'key_type': 'normal',
        'created_by': api_user_active.id
    })


def test_should_show_confirm_revoke_api_key(app_,
                                            api_user_active,
                                            mock_login,
                                            mock_get_api_keys,
                                            mock_get_service,
                                            mock_has_permissions,
                                            fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.revoke_api_key', service_id=fake_uuid, key_id=fake_uuid))

        assert response.status_code == 200
        assert 'some key name' in response.get_data(as_text=True)
        mock_get_api_keys.assert_called_once_with(service_id=fake_uuid, key_id=fake_uuid)


def test_should_redirect_after_revoking_api_key(app_,
                                                api_user_active,
                                                mock_login,
                                                mock_revoke_api_key,
                                                mock_get_api_keys,
                                                mock_get_service,
                                                mock_has_permissions,
                                                fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.post(url_for('main.revoke_api_key', service_id=fake_uuid, key_id=fake_uuid))

        assert response.status_code == 302
        assert response.location == url_for('.api_keys', service_id=fake_uuid, _external=True)
        mock_revoke_api_key.assert_called_once_with(service_id=fake_uuid, key_id=fake_uuid)
        mock_get_api_keys.assert_called_once_with(service_id=fake_uuid, key_id=fake_uuid)


def test_route_permissions(mocker,
                           app_,
                           api_user_active,
                           service_one,
                           mock_get_api_keys):
    routes = [
        'main.api_keys',
        'main.create_api_key',
        'main.revoke_api_key']
    with app_.test_request_context():
        for route in routes:
            validate_route_permission(
                mocker,
                app_,
                "GET",
                200,
                url_for(route, service_id=service_one['id'], key_id=123),
                ['manage_api_keys'],
                api_user_active,
                service_one)


def test_route_invalid_permissions(mocker,
                                   app_,
                                   api_user_active,
                                   service_one,
                                   mock_get_api_keys):
    routes = [
        'main.api_keys',
        'main.create_api_key',
        'main.revoke_api_key']
    with app_.test_request_context():
        for route in routes:
            validate_route_permission(
                mocker,
                app_,
                "GET",
                403,
                url_for(route, service_id=service_one['id'], key_id=123),
                ['view_activity'],
                api_user_active,
                service_one)


def test_should_show_whitelist_page(
    client,
    mock_login,
    api_user_active,
    mock_get_service,
    mock_has_permissions,
    mock_get_whitelist
):
    client.login(api_user_active)
    response = client.get(url_for('main.whitelist', service_id=str(uuid.uuid4())))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    textboxes = page.find_all('input', {'type': 'text'})
    for index, value in enumerate(
        ['test@example.com'] + [''] * 4 + ['07900900000'] + [''] * 4
    ):
        assert textboxes[index]['value'] == value


def test_should_update_whitelist(
    client,
    mock_login,
    api_user_active,
    mock_get_service,
    mock_has_permissions,
    mock_update_whitelist
):
    client.login(api_user_active)
    service_id = str(uuid.uuid4())
    data = OrderedDict([
        ('email_addresses-1', 'test@example.com'),
        ('email_addresses-3', 'test@example.com'),
        ('phone_numbers-0', '07900900000')
    ])
    response = client.post(
        url_for('main.whitelist', service_id=service_id),
        data=data
    )
    mock_update_whitelist.assert_called_once_with(service_id, list(data.values()))

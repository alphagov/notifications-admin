import uuid
from collections import OrderedDict

import pytest
from flask import url_for
from bs4 import BeautifulSoup
from unittest.mock import call

from tests import validate_route_permission
from tests.conftest import (
    mock_get_service,
    mock_get_live_service,
    mock_get_service_with_letters,
    normalize_spaces,
    SERVICE_ONE_ID,
)


def test_should_show_api_page(
    logged_in_client,
    mock_login,
    api_user_active,
    mock_get_service,
    mock_has_permissions,
    mock_get_notifications
):
    response = logged_in_client.get(url_for('main.api_integration', service_id=str(uuid.uuid4())))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string.strip() == 'API integration'
    rows = page.find_all('details')
    assert len(rows) == 5
    for index, row in enumerate(rows):
        assert row.find('h3').string.strip() == '07123456789'


def test_should_show_api_page_with_lots_of_notifications(
    logged_in_client,
    mock_login,
    api_user_active,
    mock_get_service,
    mock_has_permissions,
    mock_get_notifications_with_previous_next
):
    response = logged_in_client.get(url_for('main.api_integration', service_id=str(uuid.uuid4())))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    rows = page.find_all('div', {'class': 'api-notifications-item'})
    assert ' '.join(rows[len(rows) - 1].text.split()) == (
        'Only showing the first 50 messages. Notify deletes messages after 7 days.'
    )


def test_should_show_api_page_with_no_notifications(
    logged_in_client,
    mock_login,
    api_user_active,
    mock_get_service,
    mock_has_permissions,
    mock_get_notifications_with_no_notifications
):
    response = logged_in_client.get(url_for('main.api_integration', service_id=str(uuid.uuid4())))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    rows = page.find_all('div', {'class': 'api-notifications-item'})
    assert 'When you send messages via the API they’ll appear here.' in rows[len(rows) - 1].text.strip()


def test_should_show_api_page_for_live_service(
    logged_in_client,
    mock_login,
    api_user_active,
    mock_get_live_service,
    mock_has_permissions
):
    response = logged_in_client.get(url_for('main.api_integration', service_id=str(uuid.uuid4())))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert 'Your service is in trial mode' not in page.find('main').text


def test_should_show_api_documentation_page(
    logged_in_client,
    mock_login,
    api_user_active,
    mock_get_service,
    mock_has_permissions
):
    response = logged_in_client.get(url_for('main.api_documentation', service_id=str(uuid.uuid4())))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string.strip() == 'Documentation'


def test_should_show_empty_api_keys_page(
    client,
    api_user_pending,
    mock_login,
    mock_get_no_api_keys,
    mock_get_service,
    mock_has_permissions,
):
    client.login(api_user_pending)
    service_id = str(uuid.uuid4())
    response = client.get(url_for('main.api_keys', service_id=service_id))

    assert response.status_code == 200
    assert 'You haven’t created any API keys yet' in response.get_data(as_text=True)
    assert 'Create an API key' in response.get_data(as_text=True)
    mock_get_no_api_keys.assert_called_once_with(service_id=service_id)


def test_should_show_api_keys_page(
    logged_in_client,
    api_user_active,
    mock_login,
    mock_get_api_keys,
    mock_get_service,
    mock_has_permissions,
    fake_uuid,
):
    response = logged_in_client.get(url_for('main.api_keys', service_id=fake_uuid))

    assert response.status_code == 200
    resp_data = response.get_data(as_text=True)
    assert 'some key name' in resp_data
    assert 'another key name' in resp_data
    assert 'Revoked 1 January at 1:00am' in resp_data
    mock_get_api_keys.assert_called_once_with(service_id=fake_uuid)


@pytest.mark.parametrize('service_mock, expected_options', [
    (
        mock_get_service,
        [
            (
                'Live – sends to anyone '
                'Not available because your service is in trial mode'
            ),
            'Team and whitelist – limits who you can send to',
            'Test – pretends to send messages',
        ]
    ),
    (
        mock_get_live_service,
        [
            'Live – sends to anyone',
            'Team and whitelist – limits who you can send to',
            'Test – pretends to send messages',
        ]
    ),
    (
        mock_get_service_with_letters,
        [
            'Live – sends to anyone',
            (
                'Team and whitelist – limits who you can send to '
                'Can’t be used to send letters'
            ),
            'Test – pretends to send messages',
        ]
    ),
])
def test_should_show_create_api_key_page(
    client_request,
    mocker,
    api_user_active,
    mock_get_api_keys,
    service_mock,
    expected_options,
):
    service_mock(mocker, api_user_active)

    page = client_request.get('main.create_api_key', service_id=SERVICE_ONE_ID)

    for index, option in enumerate(expected_options):
        assert normalize_spaces(page.select('.block-label')[index].text) == option


def test_should_create_api_key_with_type_normal(
    logged_in_client,
    api_user_active,
    mock_login,
    mock_get_api_keys,
    mock_get_live_service,
    mock_has_permissions,
    fake_uuid,
    mocker,
):
    post = mocker.patch('app.notify_client.api_key_api_client.ApiKeyApiClient.post', return_value={'data': fake_uuid})
    service_id = str(uuid.uuid4())

    response = logged_in_client.post(
        url_for('main.create_api_key', service_id=service_id),
        data={
            'key_name': 'Some default key name 1/2',
            'key_type': 'normal'
        }
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    keys = page.find_all('span', {'class': 'api-key-key'})
    for index, key in enumerate([
        'some_default_key_name_12-{}-{}'.format(service_id, fake_uuid),
        service_id,
        fake_uuid
    ]):
        assert keys[index].text.strip() == key

    post.assert_called_once_with(url='/service/{}/api-key'.format(service_id), data={
        'name': 'Some default key name 1/2',
        'key_type': 'normal',
        'created_by': api_user_active.id
    })


def test_cant_create_normal_api_key_in_trial_mode(
    logged_in_client,
    api_user_active,
    mock_login,
    mock_get_api_keys,
    mock_get_service,
    mock_has_permissions,
    fake_uuid,
    mocker,
):
    mock_post = mocker.patch('app.notify_client.api_key_api_client.ApiKeyApiClient.post')

    response = logged_in_client.post(
        url_for('main.create_api_key', service_id=uuid.uuid4()),
        data={
            'key_name': 'some default key name',
            'key_type': 'normal'
        }
    )
    assert response.status_code == 400
    mock_post.assert_not_called()


def test_should_show_confirm_revoke_api_key(
    client_request,
    mock_get_api_keys,
    fake_uuid,
):
    page = client_request.get(
        'main.revoke_api_key', service_id=SERVICE_ONE_ID, key_id=fake_uuid,
        _test_page_title=False,
    )
    assert normalize_spaces(page.select('.banner-dangerous')[0].text) == (
        'Are you sure you want to revoke this API key? '
        '‘some key name’ will no longer let you connect to GOV.UK Notify.'
    )
    assert mock_get_api_keys.call_args_list == [
        call(
            key_id=fake_uuid,
            service_id='596364a0-858e-42c8-9062-a8fe822260eb',
        ),
        call(
            service_id='596364a0-858e-42c8-9062-a8fe822260eb'
        ),
    ]


def test_should_redirect_after_revoking_api_key(
    logged_in_client,
    api_user_active,
    mock_login,
    mock_revoke_api_key,
    mock_get_api_keys,
    mock_get_service,
    mock_has_permissions,
    fake_uuid,
):
    response = logged_in_client.post(url_for('main.revoke_api_key', service_id=fake_uuid, key_id=fake_uuid))

    assert response.status_code == 302
    assert response.location == url_for('.api_keys', service_id=fake_uuid, _external=True)
    mock_revoke_api_key.assert_called_once_with(service_id=fake_uuid, key_id=fake_uuid)
    mock_get_api_keys.assert_called_once_with(service_id=fake_uuid, key_id=fake_uuid)


@pytest.mark.parametrize('route', [
    'main.api_keys',
    'main.create_api_key',
    'main.revoke_api_key'
])
def test_route_permissions(
    mocker,
    app_,
    api_user_active,
    service_one,
    mock_get_api_keys,
    route,
):
    with app_.test_request_context():
        validate_route_permission(
            mocker,
            app_,
            "GET",
            200,
            url_for(route, service_id=service_one['id'], key_id=123),
            ['manage_api_keys'],
            api_user_active,
            service_one)


@pytest.mark.parametrize('route', [
    'main.api_keys',
    'main.create_api_key',
    'main.revoke_api_key'
])
def test_route_invalid_permissions(
    mocker,
    app_,
    api_user_active,
    service_one,
    mock_get_api_keys,
    route,
):
    with app_.test_request_context():
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
    logged_in_client,
    mock_login,
    api_user_active,
    mock_get_service,
    mock_has_permissions,
    mock_get_whitelist,
):
    response = logged_in_client.get(url_for('main.whitelist', service_id=str(uuid.uuid4())))
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    textboxes = page.find_all('input', {'type': 'text'})
    for index, value in enumerate(
        ['test@example.com'] + [''] * 4 + ['07900900000'] + [''] * 4
    ):
        assert textboxes[index]['value'] == value


def test_should_update_whitelist(
    logged_in_client,
    mock_login,
    api_user_active,
    mock_get_service,
    mock_has_permissions,
    mock_update_whitelist
):
    service_id = str(uuid.uuid4())
    data = OrderedDict([
        ('email_addresses-1', 'test@example.com'),
        ('email_addresses-3', 'test@example.com'),
        ('phone_numbers-0', '07900900000'),
        ('phone_numbers-2', '+1800-555-555'),
    ])

    response = logged_in_client.post(
        url_for('main.whitelist', service_id=service_id),
        data=data
    )

    mock_update_whitelist.assert_called_once_with(service_id, {
        'email_addresses': ['test@example.com', 'test@example.com'],
        'phone_numbers': ['07900900000', '+1800-555-555']})


def test_should_validate_whitelist_items(
    logged_in_client,
    mock_login,
    api_user_active,
    mock_get_service,
    mock_has_permissions,
    mock_update_whitelist
):

    response = logged_in_client.post(
        url_for('main.whitelist', service_id=str(uuid.uuid4())),
        data=OrderedDict([
            ('email_addresses-1', 'abc'),
            ('phone_numbers-0', '123')
        ])
    )

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string.strip() == 'There was a problem with your whitelist'
    jump_links = page.select('.banner-dangerous a')

    assert jump_links[0].string.strip() == 'Enter valid email addresses'
    assert jump_links[0]['href'] == '#email_addresses'

    assert jump_links[1].string.strip() == 'Enter valid phone numbers'
    assert jump_links[1]['href'] == '#phone_numbers'

    mock_update_whitelist.assert_not_called()

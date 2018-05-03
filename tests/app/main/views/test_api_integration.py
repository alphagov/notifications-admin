import uuid
from collections import OrderedDict
from unittest.mock import call

import pytest
from bs4 import BeautifulSoup
from flask import url_for

from tests import validate_route_permission
from tests.conftest import (
    SERVICE_ONE_ID,
    fake_uuid,
    mock_get_live_service,
    mock_get_notifications,
    mock_get_service,
    mock_get_service_with_letters,
    mock_get_valid_service_callback_api,
    mock_get_valid_service_inbound_api,
    normalize_spaces,
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


@pytest.mark.parametrize('template_type, has_links', [
    ('sms', False),
    ('letter', True),
])
def test_letter_notifications_should_have_link_to_view_letter(
    client_request,
    api_user_active,
    fake_uuid,
    mock_has_permissions,
    mocker,
    template_type,
    has_links
):
    mock_get_notifications(mocker, api_user_active, diff_template_type=template_type)

    page = client_request.get(
        'main.api_integration',
        service_id=fake_uuid,
    )

    assert (page.select_one('details a') is not None) == has_links


@pytest.mark.parametrize('status', [
    'pending-virus-check', 'virus-scan-failed'
])
def test_should_not_have_link_to_view_letter_for_precompiled_letters_in_virus_states(
    client_request,
    api_user_active,
    fake_uuid,
    mock_has_permissions,
    mocker,
    status
):
    mock_get_notifications(mocker, api_user_active, noti_status=status)

    page = client_request.get(
        'main.api_integration',
        service_id=fake_uuid,
    )

    assert not page.select_one('details a')


@pytest.mark.parametrize('client_reference, shows_ref', [
    ('foo', True),
    (None, False),
])
def test_letter_notifications_should_show_client_reference(
    client_request,
    api_user_active,
    fake_uuid,
    mock_has_permissions,
    mocker,
    client_reference,
    shows_ref
):
    mock_get_notifications(mocker, api_user_active, client_reference=client_reference)

    page = client_request.get(
        'main.api_integration',
        service_id=fake_uuid,
    )
    dt_arr = [p.text for p in page.select('dt')]

    if shows_ref:
        assert 'client_reference:' in dt_arr
        assert page.select_one('dd:nth-of-type(2)').text == 'foo'
    else:
        assert 'client_reference:' not in dt_arr


def test_should_show_api_page_for_live_service(
    client_request,
    mock_login,
    api_user_active,
    mock_get_notifications,
    mock_get_live_service,
    mock_has_permissions
):
    page = client_request.get(
        'main.api_integration',
        service_id=uuid.uuid4()
    )
    assert 'Your service is in trial mode' not in page.find('main').text


def test_api_documentation_page_should_redirect(
    logged_in_client,
    mock_login,
    api_user_active,
    mock_get_service,
    mock_has_permissions
):
    response = logged_in_client.get(url_for('main.api_documentation', service_id=str(uuid.uuid4())))
    assert response.status_code == 301
    assert response.location == url_for(
        'main.documentation',
        _external=True
    )


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
    (mock_get_service, [
        (
            'Live – sends to anyone '
            'Not available because your service is in trial mode'
        ),
        'Team and whitelist – limits who you can send to',
        'Test – pretends to send messages',
    ]),
    (mock_get_live_service, [
        'Live – sends to anyone',
        'Team and whitelist – limits who you can send to',
        'Test – pretends to send messages',
    ]),
    (mock_get_service_with_letters, [
        'Live – sends to anyone',
        (
            'Team and whitelist – limits who you can send to '
            'Can’t be used to send letters'
        ),
        'Test – pretends to send messages',
    ]),
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
        '‘some key name’ will no longer let you connect to GOV.UK Notify. '
        'Confirm'
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

    logged_in_client.post(
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


@pytest.mark.parametrize('endpoint', [
    ('main.delivery_status_callback'),
    ('main.received_text_messages_callback'),
])
@pytest.mark.parametrize('url, bearer_token, expected_errors', [
    ("", "", "Can’t be empty Can’t be empty"),
    ("http://not_https.com", "1234567890", "Must be a valid https URL"),
    ("https://test.com", "123456789", "Must be at least 10 characters"),
])
def test_callback_forms_validation(
    client_request,
    service_one,
    endpoint,
    url,
    bearer_token,
    expected_errors
):
    if endpoint == 'main.received_text_messages_callback':
        service_one['permissions'] = ['inbound_sms']

    data = {
        "url": url,
        "bearer_token": bearer_token,
    }

    response = client_request.post(
        endpoint,
        service_id=service_one['id'],
        _data=data,
        _expected_status=200
    )
    error_msgs = ' '.join(msg.text.strip() for msg in response.select(".error-message"))

    assert error_msgs == expected_errors


@pytest.mark.parametrize('has_inbound_sms, expected_link', [
    (True, 'main.api_callbacks'),
    (False, 'main.delivery_status_callback'),
])
def test_callbacks_button_links_straight_to_delivery_status_if_service_has_no_inbound_sms(
    client_request,
    service_one,
    mocker,
    mock_get_notifications,
    has_inbound_sms,
    expected_link
):
    if has_inbound_sms:
        service_one['permissions'] = ['inbound_sms']

    page = client_request.get(
        'main.api_integration',
        service_id=service_one['id'],
    )

    assert page.select('.pill-separate-item')[2]['href'] == url_for(
        expected_link, service_id=service_one['id']
    )


def test_callbacks_page_redirects_to_delivery_status_if_service_has_no_inbound_sms(
    client_request,
    service_one,
    mocker
):
    page = client_request.get(
        'main.api_callbacks',
        service_id=service_one['id'],
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one('h1').text) == "Callbacks for delivery receipts"


@pytest.mark.parametrize('has_inbound_sms, expected_link', [
    (True, 'main.api_callbacks'),
    (False, 'main.api_integration'),
])
def test_back_link_directs_to_api_integration_from_delivery_callback_if_no_inbound_sms(
    client_request,
    service_one,
    mocker,
    has_inbound_sms,
    expected_link
):
    if has_inbound_sms:
        service_one['permissions'] = ['inbound_sms']

    page = client_request.get(
        'main.delivery_status_callback',
        service_id=service_one['id'],
        _follow_redirects=True,
    )

    assert page.select_one('.page-footer-back-link')['href'] == url_for(
        expected_link, service_id=service_one['id']
    )


@pytest.mark.parametrize('endpoint', [
    ('main.delivery_status_callback'),
    ('main.received_text_messages_callback'),
])
def test_create_delivery_status_and_receive_text_message_callbacks(
    client_request,
    service_one,
    mocker,
    mock_get_notifications,
    mock_create_service_inbound_api,
    mock_create_service_callback_api,
    endpoint,
    fake_uuid,
):
    if endpoint == 'main.received_text_messages_callback':
        service_one['permissions'] = ['inbound_sms']

    data = {
        'url': "https://test.url.com/",
        'bearer_token': '1234567890',
        'user_id': fake_uuid
    }

    client_request.post(
        endpoint,
        service_id=service_one['id'],
        _data=data,
    )

    if endpoint == 'main.received_text_messages_callback':
        mock_create_service_inbound_api.assert_called_once_with(
            service_one['id'],
            url="https://test.url.com/",
            bearer_token="1234567890",
            user_id=fake_uuid,
        )
    else:
        mock_create_service_callback_api.assert_called_once_with(
            service_one['id'],
            url="https://test.url.com/",
            bearer_token="1234567890",
            user_id=fake_uuid,
        )


@pytest.mark.parametrize('endpoint, fixture', [
    ('main.delivery_status_callback', mock_get_valid_service_callback_api),
    ('main.received_text_messages_callback', mock_get_valid_service_inbound_api),
])
def test_update_delivery_status_and_receive_text_message_callbacks(
    client_request,
    service_one,
    mocker,
    mock_get_notifications,
    mock_update_service_inbound_api,
    mock_update_service_callback_api,
    endpoint,
    fixture,
    fake_uuid,
):
    if endpoint == 'main.received_text_messages_callback':
        service_one['inbound_api'] = [fake_uuid]
        service_one['permissions'] = ['inbound_sms']
    else:
        service_one['service_callback_api'] = [fake_uuid]

    fixture(mocker)

    data = {
        'url': "https://test.url.com/",
        'bearer_token': '1234567890',
        'user_id': fake_uuid
    }

    client_request.post(
        endpoint,
        service_id=service_one['id'],
        _data=data,
    )

    if endpoint == 'main.received_text_messages_callback':
        mock_update_service_inbound_api.assert_called_once_with(
            service_one['id'],
            url="https://test.url.com/",
            bearer_token="1234567890",
            user_id=fake_uuid,
            inbound_api_id=fake_uuid,
        )
    else:
        mock_update_service_callback_api.assert_called_once_with(
            service_one['id'],
            url="https://test.url.com/",
            bearer_token="1234567890",
            user_id=fake_uuid,
            callback_api_id=fake_uuid
        )


@pytest.mark.parametrize('endpoint, data, fixture', [
    (
        'main.delivery_status_callback',
        {"url": "https://hello2.gov.uk", "bearer_token": "bearer_token_set"},
        mock_get_valid_service_callback_api
    ),
    (
        'main.received_text_messages_callback',
        {"url": "https://hello3.gov.uk", "bearer_token": "bearer_token_set"},
        mock_get_valid_service_inbound_api
    ),
])
def test_update_delivery_status_and_receive_text_message_callbacks_without_changes_do_not_update(
    client_request,
    service_one,
    mocker,
    mock_get_notifications,
    mock_update_service_callback_api,
    mock_update_service_inbound_api,
    data,
    fixture,
    endpoint,
    fake_uuid,
):
    if endpoint == 'main.received_text_messages_callback':
        service_one['inbound_api'] = [fake_uuid]
        service_one['permissions'] = ['inbound_sms']
    else:
        service_one['service_callback_api'] = [fake_uuid]

    fixture(mocker)

    data['user_id'] = fake_uuid

    client_request.post(
        endpoint,
        service_id=service_one['id'],
        _data=data,
    )

    if endpoint == 'main.received_text_messages_callback':
        assert mock_update_service_inbound_api.called is False
    else:
        assert mock_update_service_callback_api.called is False


@pytest.mark.parametrize('service_callback_api, delivery_url, expected_1st_table_row', [
    (
        None, {},
        'Callbacks for delivery receipts Not set Change'
    ),
    (
        fake_uuid(), {'url': 'https://delivery.receipts'},
        'Callbacks for delivery receipts https://delivery.receipts Change'
    ),
])
@pytest.mark.parametrize('inbound_api, inbound_url, expected_2nd_table_row', [
    (
        None, {},
        'Callbacks for received text messages Not set Change'
    ),
    (
        fake_uuid(), {'url': 'https://inbound.sms'},
        'Callbacks for received text messages https://inbound.sms Change'
    ),
])
def test_callbacks_page_works_when_no_apis_set(
    client_request,
    service_one,
    mocker,
    service_callback_api,
    delivery_url,
    expected_1st_table_row,
    inbound_api,
    inbound_url,
    expected_2nd_table_row,
):
    service_one['permissions'] = ['inbound_sms']
    service_one['inbound_api'] = inbound_api
    service_one['service_callback_api'] = service_callback_api

    mocker.patch('app.service_api_client.get_service_callback_api', return_value=delivery_url)
    mocker.patch('app.service_api_client.get_service_inbound_api', return_value=inbound_url)

    page = client_request.get('main.api_callbacks',
                              service_id=service_one['id'],
                              _follow_redirects=True)
    expected_rows = [
        expected_1st_table_row,
        expected_2nd_table_row,
    ]
    rows = page.select('tbody tr')
    assert len(rows) == 2
    for index, row in enumerate(expected_rows):
        assert row == normalize_spaces(rows[index].text)

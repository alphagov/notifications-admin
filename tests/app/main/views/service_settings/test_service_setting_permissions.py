import functools

import pytest
from flask import url_for

from tests.conftest import normalize_spaces


@pytest.fixture
def get_service_settings_page(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_inbound_number_for_service,
    mock_get_all_letter_branding,
    mock_get_service_organisation,
    mock_get_free_sms_fragment_limit,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    mock_get_service_data_retention,
):
    client_request.login(platform_admin_user)
    return functools.partial(client_request.get, 'main.service_settings', service_id=service_one['id'])


def test_service_set_permission_requires_platform_admin(
    mocker,
    client_request,
    service_one,
    mock_get_inbound_number_for_service,
):
    client_request.post(
        'main.service_set_permission', service_id=service_one['id'], permission='upload_document',
        _data={'enabled': 'True'},
        _expected_status=403
    )


@pytest.mark.parametrize('permission, form_data, on', [
    ('upload_document', 'True', True),
    ('upload_document', 'False', False),
    ('inbound_sms', 'True', True),
    ('inbound_sms', 'False', False),
    ('email_auth', 'True', True),
    ('email_auth', 'False', False),
])
def test_service_set_permission(
    mocker,
    logged_in_platform_admin_client,
    service_one,
    mock_get_inbound_number_for_service,
    permission,
    form_data,
    on
):
    force_permission = mocker.patch('app.models.service.Service.force_permission')
    response = logged_in_platform_admin_client.post(
        url_for('main.service_set_permission', service_id=service_one['id'], permission=permission),
        data={'enabled': form_data}
    )
    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)
    force_permission.assert_called_with(
        permission, on=on
    )


@pytest.mark.parametrize('service_fields, endpoint, kwargs, text', [
    ({'restricted': True}, '.service_switch_live', {}, 'Live Off Change'),
    ({'restricted': False}, '.service_switch_live', {}, 'Live On Change'),
    ({'permissions': ['upload_document']},
     '.service_switch_can_upload_document', {}, 'Send files by email On Change'),
    ({'permissions': []},
     '.service_switch_can_upload_document', {}, 'Send files by email Off Change'),
    ({'permissions': ['sms']}, '.service_set_inbound_number', {}, 'Receive inbound SMS Off Change'),
    ({'permissions': ['letter']},
     '.service_set_permission', {'permission': 'upload_letters'}, 'Uploading letters Off Change'),
])
def test_service_setting_toggles_show(get_service_settings_page, service_one, service_fields, endpoint, kwargs, text):
    link_url = url_for(endpoint, **kwargs, service_id=service_one['id'])
    service_one.update(service_fields)
    page = get_service_settings_page()
    assert normalize_spaces(page.find('a', {'href': link_url}).find_parent('tr').text.strip()) == text


@pytest.mark.parametrize('service_fields, endpoint, index, text', [
    ({'active': True}, '.archive_service', 0, 'Delete this service'),
    ({'active': True}, '.suspend_service', 1, 'Suspend service'),
    ({'active': False}, '.resume_service', 0, 'Resume service'),
    pytest.param(
        {'active': False}, '.archive_service', 1, 'Resume service',
        marks=pytest.mark.xfail(raises=IndexError)
    )
])
def test_service_setting_button_toggles(
    get_service_settings_page,
    service_one,
    service_fields,
    endpoint,
    index,
    text,
):
    button_url = url_for(endpoint, service_id=service_one['id'])
    service_one.update(service_fields)
    page = get_service_settings_page()
    link = page.select('.page-footer-delete-link a')[index]
    assert normalize_spaces(link.text) == text
    assert link['href'] == button_url


@pytest.mark.parametrize('permissions,permissions_text,visible', [
    ('sms', 'inbound SMS', True),
    ('inbound_sms', 'inbound SMS', False),                 # no sms parent permission
    # also test no permissions set
    ('', 'inbound SMS', False),
])
def test_service_settings_doesnt_show_option_if_parent_permission_disabled(
    get_service_settings_page,
    service_one,
    permissions,
    permissions_text,
    visible
):
    service_one['permissions'] = [permissions]
    page = get_service_settings_page()
    cells = page.find_all('td')
    assert any(cell for cell in cells if permissions_text in cell.text) is visible


@pytest.mark.parametrize('service_fields, hidden_button_text', [
    # can't archive or suspend inactive service. Can't resume active service.
    ({'active': False}, 'Archive service'),
    ({'active': False}, 'Suspend service'),
    ({'active': True}, 'Resume service'),
])
def test_service_setting_toggles_dont_show(get_service_settings_page, service_one, service_fields, hidden_button_text):
    service_one.update(service_fields)
    page = get_service_settings_page()
    toggles = page.find_all('a', {'class': 'button'})
    assert not any(button for button in toggles if hidden_button_text in button.text)


def test_normal_user_doesnt_see_any_toggle_buttons(
    client_request,
    service_one,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    mock_get_service_organisation,
    single_sms_sender,
    mock_get_all_letter_branding,
    mock_get_inbound_number_for_service,
    mock_get_free_sms_fragment_limit,
    mock_get_service_data_retention
):
    page = client_request.get('main.service_settings', service_id=service_one['id'])
    toggles = page.find('a', {'class': 'button'})
    assert toggles is None

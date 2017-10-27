import functools

import pytest
from flask import url_for

from tests.conftest import client_request as client_request_factory


@pytest.fixture
def get_service_settings_page(
    logged_in_platform_admin_client,
    service_one,
    mock_get_inbound_number_for_service,
    mock_get_letter_organisations,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
):
    platform_admin_request = client_request_factory(logged_in_platform_admin_client)
    return functools.partial(platform_admin_request.get, 'main.service_settings', service_id=service_one['id'])


@pytest.mark.parametrize('service_fields, endpoint, kwargs, text', [
    ({'restricted': True}, '.service_switch_live', {}, 'Make service live'),
    ({'restricted': False}, '.service_switch_live', {}, 'Revert service to trial mode'),

    ({'research_mode': True}, '.service_switch_research_mode', {}, 'Take service out of research mode'),
    ({'research_mode': False}, '.service_switch_research_mode', {}, 'Put into research mode'),

    ({'permissions': ['email']}, '.service_switch_can_send_email', {}, 'Stop sending emails'),
    ({'permissions': []}, '.service_switch_can_send_email', {}, 'Allow to send emails'),

    ({'permissions': ['letter']}, '.service_switch_can_send_letters', {}, 'Stop sending letters'),
    ({'permissions': []}, '.service_switch_can_send_letters', {}, 'Allow to send letters'),

    ({'permissions': ['sms']}, '.service_switch_can_send_sms', {}, 'Stop sending sms'),
    ({'permissions': []}, '.service_switch_can_send_sms', {}, 'Allow to send sms'),

    ({'permissions': ['sms', 'inbound_sms']}, '.service_set_inbound_number', {'set_inbound_sms': False}, 'Stop inbound sms'),  # noqa
    ({'permissions': ['sms']}, '.service_set_inbound_number', {'set_inbound_sms': True}, 'Allow inbound sms'),

    ({'active': True}, '.archive_service', {}, 'Archive service'),
    ({'active': True}, '.suspend_service', {}, 'Suspend service'),
    ({'active': False}, '.resume_service', {}, 'Resume service'),
])
def test_service_setting_toggles_show(get_service_settings_page, service_one, service_fields, endpoint, kwargs, text):
    button_url = url_for(endpoint, **kwargs, service_id=service_one['id'])
    service_one.update(service_fields)
    page = get_service_settings_page()
    assert page.find('a', {'class': 'button', 'href': button_url}).text.strip() == text


@pytest.mark.parametrize('permissions', [
    ['inbound_sms'], []
])
def test_service_settings_doesnt_show_inbound_options_if_sms_disabled(
    get_service_settings_page,
    service_one,
    permissions
):
    service_one['permissions'] = permissions
    page = get_service_settings_page()
    toggles = page.find_all('a', {'class': 'button'})
    assert not any(button for button in toggles if 'inbound sms' in button.text)


@pytest.mark.parametrize('service_fields, hidden_button_text', [
    # if no sms permission, inbound sms shouldn't show
    ({'permissions': ['inbound_sms']}, 'Stop inbound sms'),
    ({'permissions': []}, 'Allow inbound sms'),

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

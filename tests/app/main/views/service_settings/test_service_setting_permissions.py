import functools

import pytest
from flask import url_for

from tests.conftest import client_request as client_request_factory


@pytest.fixture
def get_service_settings_page(
    logged_in_platform_admin_client,
    service_one,
    mock_get_inbound_number_for_service,
    mock_get_letter_email_branding,
    mock_get_service_organisation,
    mock_get_free_sms_fragment_limit,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
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

    ({'permissions': ['sms']}, '.service_switch_can_send_sms', {}, 'Stop sending sms'),
    ({'permissions': []}, '.service_switch_can_send_sms', {}, 'Allow to send sms'),

    ({'permissions': ['letter', 'precompiled_letter']},
        '.service_switch_can_send_precompiled_letter', {}, 'Stop sending precompiled letters'),
    ({'permissions': ['letter']},
        '.service_switch_can_send_precompiled_letter', {}, 'Allow to send precompiled letters'),

    ({'permissions': ['upload_document']},
        '.service_switch_can_upload_document', {}, 'Stop uploading documents'),
    ({'permissions': []},
        '.service_switch_can_upload_document', {}, 'Allow to upload documents'),

    ({'permissions': []},
        '.service_switch_caseworking', {}, 'Allow granting of caseworking permission'),
    ({'permissions': ['caseworking']},
        '.service_switch_caseworking', {}, 'Stop granting of caseworking permission'),

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


@pytest.mark.parametrize('permissions,permissions_text', [
    ('inbound_sms', 'inbound sms'),                 # no sms parent permission
    ('precompiled_letter', 'precompiled letters'),  # no letter parent permission
    # also test no permissions set
    ('', 'inbound sms'),
    ('', 'precompiled letters')
])
def test_service_settings_doesnt_show_option_if_parent_permission_disabled(
    get_service_settings_page,
    service_one,
    permissions,
    permissions_text
):
    service_one['permissions'] = [permissions]
    page = get_service_settings_page()
    toggles = page.find_all('a', {'class': 'button'})
    assert not any(button for button in toggles if permissions_text in button.text)


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


def test_normal_user_doesnt_see_any_toggle_buttons(
    client_request,
    service_one,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    mock_get_service_organisation,
    single_sms_sender,
    mock_get_letter_email_branding,
    mock_get_inbound_number_for_service,
    mock_get_free_sms_fragment_limit,
):
    page = client_request.get('main.service_settings', service_id=service_one['id'])
    toggles = page.find('a', {'class': 'button'})
    assert toggles is None

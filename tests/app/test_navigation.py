import pytest
from flask import Flask

from app import create_app
from app.navigation import (
    CaseworkNavigation,
    HeaderNavigation,
    MainNavigation,
    Navigation,
    OrgNavigation,
)
from tests.conftest import ORGANISATION_ID, SERVICE_ONE_ID, normalize_spaces

EXCLUDED_ENDPOINTS = tuple(map(Navigation.get_endpoint_with_blueprint, {
    'accept_invite',
    'accept_org_invite',
    'accessibility_statement',
    'action_blocked',
    'add_data_retention',
    'add_organisation',
    'add_organisation_from_gp_service',
    'add_organisation_from_nhs_local_service',
    'add_service',
    'add_service_template',
    'api_callbacks',
    'api_documentation',
    'api_integration',
    'api_keys',
    'approve_broadcast_message',
    'archive_organisation',
    'archive_service',
    'archive_user',
    'bat_phone',
    'begin_tour',
    'billing_details',
    'branding_and_customisation',
    'broadcast',
    'broadcast_dashboard',
    'broadcast_dashboard_previous',
    'broadcast_dashboard_rejected',
    'broadcast_dashboard_updates',
    'broadcast_tour',
    'broadcast_tour_live',
    'callbacks',
    'cancel_broadcast_message',
    'cancel_invited_org_user',
    'cancel_invited_user',
    'cancel_job',
    'cancel_letter',
    'cancel_letter_job',
    'change_user_auth',
    'check_and_resend_text_code',
    'check_and_resend_verification_code',
    'check_contact_list',
    'check_messages',
    'check_notification',
    'check_tour_notification',
    'choose_account',
    'choose_broadcast_area',
    'choose_broadcast_library',
    'choose_broadcast_sub_area',
    'choose_from_contact_list',
    'choose_service',
    'choose_template',
    'choose_template_to_copy',
    'clear_cache',
    'confirm_edit_user_email',
    'confirm_edit_user_mobile_number',
    'confirm_redact_template',
    'contact_list',
    'conversation',
    'conversation_reply',
    'conversation_reply_with_template',
    'conversation_updates',
    'cookies',
    'copy_template',
    'count_content_length',
    'create_and_send_messages',
    'create_api_key',
    'create_email_branding',
    'create_letter_branding',
    'data_retention',
    'delete_contact_list',
    'delete_service_template',
    'delete_template_folder',
    'delivery_and_failure',
    'delivery_status_callback',
    'design_content',
    'documentation',
    'download_contact_list',
    'download_notifications_csv',
    'download_organisation_usage_report',
    'edit_and_format_messages',
    'edit_data_retention',
    'edit_organisation_agreement',
    'edit_organisation_billing_details',
    'edit_organisation_crown_status',
    'edit_organisation_domains',
    'edit_organisation_email_branding',
    'edit_organisation_go_live_notes',
    'edit_organisation_letter_branding',
    'edit_organisation_name',
    'edit_organisation_notes',
    'edit_organisation_type',
    'edit_organisation_user',
    'edit_service_billing_details',
    'edit_service_notes',
    'edit_service_template',
    'edit_sms_provider_ratio',
    'edit_template_postage',
    'edit_user_email',
    'edit_user_mobile_number',
    'edit_user_permissions',
    'email_branding',
    'email_branding_govuk',
    'email_branding_govuk_and_org',
    'email_branding_nhs',
    'email_branding_organisation',
    'email_branding_request',
    'email_branding_something_else',
    'email_not_received',
    'email_template',
    'error',
    'estimate_usage',
    'features',
    'features_email',
    'features_letters',
    'features_sms',
    'feedback',
    'find_services_by_name',
    'find_users_by_email',
    'forgot_password',
    'get_billing_report',
    'get_daily_volumes',
    'get_daily_sms_provider_volumes',
    'get_volumes_by_service',
    'get_example_csv',
    'get_notifications_as_json',
    'get_started',
    'get_started_old',
    'go_to_dashboard_after_tour',
    'guest_list',
    'guidance_index',
    'history',
    'how_to_pay',
    'inbound_sms_admin',
    'inbox',
    'inbox_download',
    'inbox_updates',
    'index',
    'information_risk_management',
    'information_security',
    'integration_testing',
    'invite_org_user',
    'invite_user',
    'letter_branding',
    'letter_branding_request',
    'letter_spec',
    'letter_specification',
    'letter_template',
    'link_service_to_organisation',
    'live_services',
    'live_services_csv',
    'manage_org_users',
    'manage_template_folder',
    'manage_users',
    'message_status',
    'monthly',
    'new_broadcast',
    'new_password',
    'no_cookie.check_messages_preview',
    'no_cookie.check_notification_preview',
    'no_cookie.letter_branding_preview_image',
    'no_cookie.send_test_preview',
    'no_cookie.view_letter_template_preview',
    'no_cookie.view_template_version_preview',
    'notifications_sent_by_service',
    'old_guest_list',
    'old_integration_testing',
    'old_roadmap',
    'old_service_dashboard',
    'old_terms',
    'old_using_notify',
    'organisation_billing',
    'organisation_dashboard',
    'organisation_download_agreement',
    'organisation_preview_email_branding',
    'organisation_preview_letter_branding',
    'organisation_settings',
    'organisation_trial_mode_services',
    'organisations',
    'performance',
    'platform_admin',
    'platform_admin_list_complaints',
    'platform_admin_reports',
    'platform_admin_returned_letters',
    'platform_admin_splash_page',
    'preview_broadcast_areas',
    'preview_broadcast_message',
    'pricing',
    'privacy',
    'public_agreement',
    'public_download_agreement',
    'received_text_messages_callback',
    'redact_template',
    'register',
    'register_from_invite',
    'register_from_org_invite',
    'registration_continue',
    'reject_broadcast_message',
    'remove_broadcast_area',
    'remove_user_from_organisation',
    'remove_user_from_service',
    'request_to_go_live',
    'resend_email_link',
    'resend_email_verification',
    'resume_service',
    'returned_letter_summary',
    'returned_letters',
    'returned_letters_report',
    'revalidate_email_sent',
    'revoke_api_key',
    'roadmap',
    'save_contact_list',
    'security',
    'security_policy',
    'send_files_by_email',
    'send_files_by_email_contact_details',
    'send_from_contact_list',
    'send_messages',
    'send_notification',
    'send_one_off',
    'send_one_off_letter_address',
    'send_one_off_step',
    'send_one_off_to_myself',
    'send_uploaded_letter',
    'service_accept_agreement',
    'service_add_email_reply_to',
    'service_add_letter_contact',
    'service_add_sms_sender',
    'service_agreement',
    'service_confirm_agreement',
    'service_confirm_delete_email_reply_to',
    'service_confirm_delete_letter_contact',
    'service_confirm_delete_sms_sender',
    'service_dashboard',
    'service_dashboard_updates',
    'service_delete_email_reply_to',
    'service_delete_letter_contact',
    'service_delete_sms_sender',
    'service_download_agreement',
    'service_edit_email_reply_to',
    'service_edit_letter_contact',
    'service_edit_sms_sender',
    'service_email_reply_to',
    'service_letter_contact_details',
    'service_make_blank_default_letter_contact',
    'service_name_change',
    'service_preview_email_branding',
    'service_preview_letter_branding',
    'service_set_auth_type',
    'service_confirm_broadcast_account_type',
    'service_set_broadcast_channel',
    'service_set_broadcast_network',
    'service_set_channel',
    'service_set_email_branding',
    'service_set_inbound_number',
    'service_set_inbound_sms',
    'service_set_international_letters',
    'service_set_international_sms',
    'service_set_letter_branding',
    'service_set_letters',
    'service_set_permission',
    'service_set_reply_to_email',
    'service_set_sms_prefix',
    'service_settings',
    'service_sms_senders',
    'service_switch_count_as_live',
    'service_switch_live',
    'service_verify_reply_to_address',
    'service_verify_reply_to_address_updates',
    'services_or_dashboard',
    'set_free_sms_allowance',
    'set_message_limit',
    'set_rate_limit',
    'set_sender',
    'set_template_sender',
    'show_accounts_or_dashboard',
    'sign_in',
    'sign_out',
    'start_job',
    'submit_request_to_go_live',
    'support',
    'support_public',
    'suspend_service',
    'template_history',
    'template_usage',
    'terms',
    'thanks',
    'tour_step',
    'triage',
    'trial_mode',
    'trial_mode_new',
    'trial_services',
    'two_factor_sms',
    'two_factor_email',
    'two_factor_email_interstitial',
    'two_factor_email_sent',
    'two_factor_webauthn',
    'update_email_branding',
    'update_letter_branding',
    'upload_a_letter',
    'upload_contact_list',
    'upload_letter',
    'uploaded_letter_preview',
    'uploaded_letters',
    'uploads',
    'usage',
    'user_information',
    'user_profile',
    'user_profile_confirm_delete_mobile_number',
    'user_profile_confirm_delete_security_key',
    'user_profile_delete_security_key',
    'user_profile_disable_platform_admin_view',
    'user_profile_email',
    'user_profile_email_authenticate',
    'user_profile_email_confirm',
    'user_profile_manage_security_key',
    'user_profile_mobile_number',
    'user_profile_mobile_number_authenticate',
    'user_profile_mobile_number_confirm',
    'user_profile_mobile_number_delete',
    'user_profile_name',
    'user_profile_password',
    'user_profile_security_keys',
    'using_notify',
    'verify',
    'verify_email',
    'view_current_broadcast',
    'view_job',
    'view_job_csv',
    'view_job_updates',
    'view_jobs',
    'view_letter_notification_as_preview',
    'view_letter_upload_as_preview',
    'view_notification',
    'view_notification_updates',
    'view_notifications',
    'view_notifications_csv',
    'view_previous_broadcast',
    'view_provider',
    'view_providers',
    'view_rejected_broadcast',
    'view_template',
    'view_template_version',
    'view_template_versions',
    'webauthn_begin_register',
    'webauthn_complete_register',
    'webauthn_begin_authentication',
    'webauthn_complete_authentication',
    'who_can_use_notify',
    'who_its_for',
    'write_new_broadcast',
}))


def flask_app():
    app = Flask('app')
    create_app(app)

    ctx = app.app_context()
    ctx.push()

    yield app


all_endpoints = [
    rule.endpoint for rule in next(flask_app()).url_map.iter_rules()
]

navigation_instances = (
    MainNavigation(),
    HeaderNavigation(),
    OrgNavigation(),
    CaseworkNavigation(),
)


@pytest.mark.parametrize(
    'navigation_instance',
    navigation_instances,
    ids=(x.__class__.__name__ for x in navigation_instances)
)
def test_navigation_items_are_properly_defined(navigation_instance):
    for endpoint in navigation_instance.endpoints_with_navigation:
        assert (
            endpoint in all_endpoints
        ), '{} is not a real endpoint (in {}.mapping)'.format(
            endpoint,
            type(navigation_instance).__name__
        )
        assert (
            navigation_instance.endpoints_with_navigation.count(endpoint) == 1
        ), '{} found more than once in {}.mapping'.format(
            endpoint,
            type(navigation_instance).__name__
        )


def test_excluded_navigation_items_are_properly_defined():
    for endpoint in EXCLUDED_ENDPOINTS:
        assert (
            endpoint in all_endpoints
        ), f'{endpoint} is not a real endpoint (in EXCLUDED_ENDPOINTS)'

        assert (
            EXCLUDED_ENDPOINTS.count(endpoint) == 1
        ), f'{endpoint} found more than once in EXCLUDED_ENDPOINTS'


@pytest.mark.parametrize(
    'navigation_instance',
    navigation_instances,
    ids=(x.__class__.__name__ for x in navigation_instances)
)
def test_all_endpoints_are_covered(navigation_instance):
    covered_endpoints = (
        navigation_instance.endpoints_with_navigation +
        EXCLUDED_ENDPOINTS +
        ('static', 'status.show_status', 'metrics')
    )

    for endpoint in all_endpoints:
        assert endpoint in covered_endpoints, f'{endpoint} is not listed or excluded'


@pytest.mark.parametrize(
    'navigation_instance',
    navigation_instances,
    ids=(x.__class__.__name__ for x in navigation_instances)
)
@pytest.mark.xfail(raises=KeyError)
def test_raises_on_invalid_navigation_item(
    client_request, navigation_instance
):
    navigation_instance.is_selected('foo')


@pytest.mark.parametrize('endpoint, selected_nav_item', [
    ('main.choose_template', 'Templates'),
    ('main.manage_users', 'Team members'),
])
def test_a_page_should_nave_selected_navigation_item(
    client_request,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_get_template_folders,
    mock_get_api_keys,
    endpoint,
    selected_nav_item,
):
    page = client_request.get(endpoint, service_id=SERVICE_ONE_ID)
    selected_nav_items = page.select('.navigation a.selected')
    assert len(selected_nav_items) == 1
    assert selected_nav_items[0].text.strip() == selected_nav_item


@pytest.mark.parametrize('endpoint, selected_nav_item', [
    ('main.documentation', 'Documentation'),
    ('main.support', 'Support'),
])
def test_a_page_should_nave_selected_header_navigation_item(
    client_request,
    endpoint,
    selected_nav_item,
):
    page = client_request.get(endpoint, service_id=SERVICE_ONE_ID)
    selected_nav_items = page.select('.govuk-header__navigation-item--active')
    assert len(selected_nav_items) == 1
    assert selected_nav_items[0].text.strip() == selected_nav_item


@pytest.mark.parametrize('endpoint, selected_nav_item', [
    ('main.organisation_dashboard', 'Usage'),
    ('main.manage_org_users', 'Team members'),
])
def test_a_page_should_nave_selected_org_navigation_item(
    client_request,
    mock_get_organisation,
    mock_get_users_for_organisation,
    mock_get_invited_users_for_organisation,
    endpoint,
    selected_nav_item,
    mocker
):
    mocker.patch(
        'app.organisations_client.get_services_and_usage', return_value={'services': {}}
    )
    page = client_request.get(endpoint, org_id=ORGANISATION_ID)
    selected_nav_items = page.select('.navigation a.selected')
    assert len(selected_nav_items) == 1
    assert selected_nav_items[0].text.strip() == selected_nav_item


def test_navigation_urls(
    client_request,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_api_keys,
):
    page = client_request.get('main.choose_template', service_id=SERVICE_ONE_ID)
    assert [
        a['href'] for a in page.select('.navigation a')
    ] == [
        '/services/{}'.format(SERVICE_ONE_ID),
        '/services/{}/templates'.format(SERVICE_ONE_ID),
        '/services/{}/uploads'.format(SERVICE_ONE_ID),
        '/services/{}/users'.format(SERVICE_ONE_ID),
        '/services/{}/usage'.format(SERVICE_ONE_ID),
        '/services/{}/service-settings'.format(SERVICE_ONE_ID),
        '/services/{}/api'.format(SERVICE_ONE_ID),
    ]


def test_navigation_for_services_with_broadcast_permission(
    mocker,
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_api_keys,
    active_user_create_broadcasts_permission,
):
    service_one['permissions'] += ['broadcast']
    mocker.patch(
        'app.user_api_client.get_user',
        return_value=active_user_create_broadcasts_permission
    )

    page = client_request.get('main.choose_template', service_id=SERVICE_ONE_ID)
    assert [
        a['href'] for a in page.select('.navigation a')
    ] == [
        '/services/{}/current-alerts'.format(SERVICE_ONE_ID),
        '/services/{}/past-alerts'.format(SERVICE_ONE_ID),
        '/services/{}/rejected-alerts'.format(SERVICE_ONE_ID),
        '/services/{}/templates'.format(SERVICE_ONE_ID),
        '/services/{}/users'.format(SERVICE_ONE_ID),
    ]


def test_navigation_for_services_with_broadcast_permission_platform_admin(
    mocker,
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_api_keys,
    platform_admin_user,
):
    service_one['permissions'] += ['broadcast']
    mocker.patch(
        'app.user_api_client.get_user',
        return_value=platform_admin_user,
    )

    page = client_request.get('main.choose_template', service_id=SERVICE_ONE_ID)
    assert [
        a['href'] for a in page.select('.navigation a')
    ] == [
        '/services/{}/current-alerts'.format(SERVICE_ONE_ID),
        '/services/{}/past-alerts'.format(SERVICE_ONE_ID),
        '/services/{}/rejected-alerts'.format(SERVICE_ONE_ID),
        '/services/{}/templates'.format(SERVICE_ONE_ID),
        '/services/{}/users'.format(SERVICE_ONE_ID),
        '/services/{}/service-settings'.format(SERVICE_ONE_ID),
        '/services/{}/api/keys'.format(SERVICE_ONE_ID),
    ]


def test_caseworkers_get_caseworking_navigation(
    client_request,
    mocker,
    mock_get_template_folders,
    mock_get_service_templates,
    mock_has_no_jobs,
    mock_get_api_keys,
    active_caseworking_user,
):
    mocker.patch(
        'app.user_api_client.get_user',
        return_value=active_caseworking_user
    )
    page = client_request.get('main.choose_template', service_id=SERVICE_ONE_ID)
    assert normalize_spaces(page.select_one('header + .govuk-width-container nav').text) == (
        'Templates Sent messages Uploads Team members'
    )


def test_caseworkers_see_jobs_nav_if_jobs_exist(
    client_request,
    mocker,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_has_jobs,
    active_caseworking_user,
    mock_get_api_keys,
):
    mocker.patch(
        'app.user_api_client.get_user',
        return_value=active_caseworking_user
    )
    page = client_request.get('main.choose_template', service_id=SERVICE_ONE_ID)
    assert normalize_spaces(page.select_one('header + .govuk-width-container nav').text) == (
        'Templates Sent messages Uploads Team members'
    )

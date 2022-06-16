from itertools import chain

from flask import request


class Navigation:

    mapping = {}
    selected_class = "selected"

    def __init__(self):
        self.mapping = {
            navigation: {
                # if not specified, assume endpoints are all in the `main` blueprint.
                self.get_endpoint_with_blueprint(endpoint) for endpoint in endpoints
            } for navigation, endpoints in self.mapping.items()
        }

    @property
    def endpoints_with_navigation(self):
        return tuple(chain.from_iterable((
            endpoints
            for navigation_item, endpoints in self.mapping.items()
        )))

    def is_selected(self, navigation_item):
        if request.endpoint in self.mapping[navigation_item]:
            return " " + self.selected_class
        return ''

    @staticmethod
    def get_endpoint_with_blueprint(endpoint):
        return endpoint if '.' in endpoint else 'main.{}'.format(endpoint)


class HeaderNavigation(Navigation):

    mapping = {
        'support': {
            'bat_phone',
            'feedback',
            'support',
            'support_public',
            'thanks',
            'triage',
        },
        'features': {
            'features',
            'features_email',
            'features_letters',
            'features_sms',
            'message_status',
            'roadmap',
            'security',
            'terms',
            'trial_mode_new',
            'using_notify',
        },
        'pricing': {
            'pricing',
            'how_to_pay',
            'billing_details',
        },
        'documentation': {
            'documentation',
            'integration_testing',
        },
        'user-profile': {
            'user_profile',
            'user_profile_confirm_delete_mobile_number',
            'user_profile_email',
            'user_profile_email_authenticate',
            'user_profile_email_confirm',
            'user_profile_mobile_number',
            'user_profile_mobile_number_authenticate',
            'user_profile_mobile_number_confirm',
            'user_profile_mobile_number_delete',
            'user_profile_name',
            'user_profile_password',
            'user_profile_disable_platform_admin_view',
        },
        'platform-admin': {
            'archive_user',
            'change_user_auth',
            'clear_cache',
            'create_email_branding',
            'create_letter_branding',
            'edit_sms_provider_ratio',
            'email_branding',
            'find_services_by_name',
            'find_users_by_email',
            'letter_branding',
            'live_services',
            'live_services_csv',
            'notifications_sent_by_service',
            'get_billing_report',
            'get_daily_volumes',
            'get_daily_sms_provider_volumes',
            'get_volumes_by_service',
            'organisations',
            'platform_admin',
            'platform_admin_list_complaints',
            'platform_admin_reports',
            'platform_admin_returned_letters',
            'platform_admin_splash_page',
            'suspend_service',
            'trial_services',
            'update_email_branding',
            'update_letter_branding',
            'user_information',
            'view_provider',
            'view_providers',
        },
        'sign-in': {
            'revalidate_email_sent',
            'sign_in',
            'two_factor_sms',
            'two_factor_email',
            'two_factor_email_sent',
            'two_factor_email_interstitial',
            'two_factor_webauthn',
            'verify',
            'verify_email',
        },
    }

    # header HTML now comes from GOVUK Frontend so requires a boolean, not an attribute
    def is_selected(self, navigation_item):
        return request.endpoint in self.mapping[navigation_item]


class MainNavigation(Navigation):

    mapping = {
        'dashboard': {
            'broadcast_tour',
            'conversation',
            'inbox',
            'monthly',
            'returned_letter_summary',
            'returned_letters',
            'service_dashboard',
            'template_usage',
            'view_notification',
            'view_notifications',
        },
        'current-broadcasts': {
            'broadcast_dashboard',
            'broadcast_dashboard_updates',
            'view_current_broadcast',
            'new_broadcast',
            'write_new_broadcast',
        },
        'previous-broadcasts': {
            'broadcast_dashboard_previous',
            'view_previous_broadcast',
        },
        'rejected-broadcasts': {
            'broadcast_dashboard_rejected',
            'view_rejected_broadcast',
        },
        'templates': {
            'action_blocked',
            'add_service_template',
            'check_messages',
            'check_notification',
            'choose_from_contact_list',
            'choose_template',
            'choose_template_to_copy',
            'confirm_redact_template',
            'conversation_reply',
            'copy_template',
            'delete_service_template',
            'edit_service_template',
            'edit_template_postage',
            'manage_template_folder',
            'send_messages',
            'send_one_off',
            'send_one_off_letter_address',
            'send_one_off_step',
            'send_one_off_to_myself',
            'no_cookie.send_test_preview',
            'set_sender',
            'set_template_sender',
            'view_template',
            'view_template_version',
            'view_template_versions',
            'broadcast',
            'preview_broadcast_areas',
            'choose_broadcast_library',
            'choose_broadcast_area',
            'choose_broadcast_sub_area',
            'remove_broadcast_area',
            'preview_broadcast_message',
            'approve_broadcast_message',
            'reject_broadcast_message',
            'cancel_broadcast_message',
        },
        'uploads': {
            'upload_contact_list',
            'check_contact_list',
            'save_contact_list',
            'contact_list',
            'delete_contact_list',
            'upload_letter',
            'uploaded_letter_preview',
            'uploaded_letters',
            'uploads',
            'view_job',
            'view_jobs',
        },
        'team-members': {
            'confirm_edit_user_email',
            'confirm_edit_user_mobile_number',
            'edit_user_email',
            'edit_user_mobile_number',
            'edit_user_permissions',
            'invite_user',
            'manage_users',
            'remove_user_from_service',
        },
        'usage': {
            'usage',
        },
        'settings': {
            'add_organisation_from_gp_service',
            'add_organisation_from_nhs_local_service',
            'email_branding_govuk',
            'email_branding_govuk_and_org',
            'email_branding_nhs',
            'email_branding_organisation',
            'email_branding_request',
            'email_branding_something_else',
            'estimate_usage',
            'letter_branding_request',
            'link_service_to_organisation',
            'request_to_go_live',
            'service_add_email_reply_to',
            'service_add_letter_contact',
            'service_add_sms_sender',
            'service_agreement',
            'service_accept_agreement',
            'service_confirm_agreement',
            'service_confirm_delete_email_reply_to',
            'service_confirm_delete_letter_contact',
            'service_confirm_delete_sms_sender',
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
            'service_set_channel',
            'send_files_by_email_contact_details',
            'service_confirm_broadcast_account_type',
            'service_set_broadcast_channel',
            'service_set_broadcast_network',
            'service_set_email_branding',
            'service_set_inbound_number',
            'service_set_inbound_sms',
            'service_set_international_letters',
            'service_set_international_sms',
            'service_set_letters',
            'service_set_reply_to_email',
            'service_set_sms_prefix',
            'service_verify_reply_to_address',
            'service_verify_reply_to_address_updates',
            'service_settings',
            'service_sms_senders',
            'set_free_sms_allowance',
            'set_message_limit',
            'set_rate_limit',
            'service_set_letter_branding',
            'submit_request_to_go_live',
        },
        'api-integration': {
            'api_callbacks',
            'api_documentation',
            'api_integration',
            'api_keys',
            'create_api_key',
            'delivery_status_callback',
            'received_text_messages_callback',
            'revoke_api_key',
            'guest_list',
            'old_guest_list',
        },
    }


class CaseworkNavigation(Navigation):

    mapping = {
        'dashboard': {
            'broadcast_tour',
            'broadcast_dashboard',
            'broadcast_dashboard_previous',
            'broadcast_dashboard_updates',
        },
        'send-one-off': {
            'choose_from_contact_list',
            'choose_template',
            'send_one_off',
            'send_one_off_letter_address',
            'send_one_off_step',
            'send_one_off_to_myself',
        },
        'sent-messages': {
            'view_notifications',
            'view_notification',
        },
        'uploads': {
            'view_jobs',
            'view_job',
            'upload_contact_list',
            'check_contact_list',
            'save_contact_list',
            'contact_list',
            'delete_contact_list',
            'upload_letter',
            'uploaded_letter_preview',
            'uploaded_letters',
            'uploads',
        },
    }


class OrgNavigation(Navigation):

    mapping = {
        'dashboard': {
            'organisation_dashboard',
        },
        'settings': {
            'archive_organisation',
            'edit_organisation_agreement',
            'edit_organisation_billing_details',
            'edit_organisation_crown_status',
            'edit_organisation_domains',
            'edit_organisation_email_branding',
            'edit_organisation_letter_branding',
            'edit_organisation_domains',
            'edit_organisation_go_live_notes',
            'edit_organisation_name',
            'edit_organisation_notes',
            'edit_organisation_type',
            'organisation_preview_email_branding',
            'organisation_preview_letter_branding',
            'organisation_settings',

        },
        'team-members': {
            'edit_organisation_user',
            'invite_org_user',
            'manage_org_users',
            'remove_user_from_organisation',
        },
        'trial-services': {
            'organisation_trial_mode_services',
        },
        'billing': {
            'organisation_billing',
        }
    }

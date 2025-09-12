from itertools import chain

from flask import request, url_for


class Navigation:
    mapping = {}
    selected_class = "selected"

    def __init__(self):
        self.mapping = {
            navigation: {
                # if not specified, assume endpoints are all in the `main` blueprint.
                self.get_endpoint_with_blueprint(endpoint)
                for endpoint in endpoints
            }
            for navigation, endpoints in self.mapping.items()
        }

    @property
    def endpoints_with_navigation(self):
        return tuple(chain.from_iterable((endpoints for navigation_item, endpoints in self.mapping.items())))

    def is_selected(self, navigation_item):
        if request.endpoint in self.mapping[navigation_item]:
            return " " + self.selected_class
        return ""

    @staticmethod
    def get_endpoint_with_blueprint(endpoint):
        return endpoint if "." in endpoint else f"main.{endpoint}"


class HeaderNavigation(Navigation):
    mapping = {
        "support": {
            "bat_phone",
            "feedback",
            "support",
            "support_public",
            "thanks",
            "triage",
        },
        "features": {
            "guidance_features",
            "guidance_roadmap",
            "guidance_security",
            "guidance_who_can_use_notify",
            "performance",
        },
        "pricing": {
            "guidance_pricing",
            "guidance_pricing_text_messages",
            "guidance_pricing_letters",
            "guidance_trial_mode",
            "guidance_how_to_pay",
            "guidance_billing_details",
        },
        "using-notify": {
            "guidance_using_notify",
            "guidance_api_documentation",
            "guidance_attach_pages",
            "guidance_bulk_sending",
            "guidance_data_retention_period",
            "guidance_delivery_times",
            "guidance_email_branding",
            "guidance_formatting",
            "guidance_letter_branding",
            "guidance_links_and_URLs",
            "guidance_message_status",
            "guidance_optional_content",
            "guidance_personalisation",
            "guidance_qr_codes",
            "guidance_receive_text_messages",
            "guidance_reply_to_email_address",
            "guidance_schedule_messages",
            "guidance_send_files_by_email",
            "guidance_sign_in_method",
            "guidance_team_members_and_permissions",
            "guidance_templates",
            "guidance_text_message_sender",
            "guidance_unsubscribe_links",
            "guidance_upload_a_letter",
        },
        "your-account": {
            "your_account",
            "your_account_confirm_delete_mobile_number",
            "your_account_delete_security_key",
            "your_account_disable_platform_admin_view",
            "your_account_email",
            "your_account_email_authenticate",
            "your_account_email_confirm",
            "your_account_get_emails_about_new_features",
            "your_account_manage_security_key",
            "your_account_mobile_number",
            "your_account_mobile_number_authenticate",
            "your_account_mobile_number_confirm",
            "your_account_mobile_number_delete",
            "your_account_name",
            "your_account_password",
            "your_account_security_keys",
            "your_account_take_part_in_user_research",
        },
        "platform-admin": {
            "archive_user",
            "change_user_auth",
            "clear_cache",
            "create_letter_branding",
            "edit_sms_provider_ratio",
            "email_branding",
            "letter_branding",
            "live_services_csv",
            "notifications_sent_by_service",
            "get_billing_report",
            "platform_admin_users_list",
            "get_daily_volumes",
            "get_dvla_billing_report",
            "get_daily_sms_provider_volumes",
            "get_volumes_by_service",
            "organisations",
            "platform_admin_list_complaints",
            "platform_admin_reports",
            "platform_admin_returned_letters",
            "platform_admin_search",
            "platform_admin_archive_email_branding",
            "platform_admin_confirm_archive_email_branding",
            "platform_admin_create_email_branding",
            "platform_admin_update_email_branding",
            "platform_admin_view_email_branding",
            "update_letter_branding",
            "user_information",
            "view_provider",
            "view_providers",
        },
        "sign-in": {
            "revalidate_email_sent",
            "sign_in",
            "two_factor_sms",
            "two_factor_email",
            "two_factor_email_sent",
            "two_factor_email_interstitial",
            "two_factor_webauthn",
            "verify",
            "verify_email",
        },
    }

    # header HTML now comes from GOVUK Frontend so requires a boolean, not an attribute
    def is_selected(self, navigation_item):
        return request.endpoint in self.mapping[navigation_item]

    def visible_header_nav(self):
        from app import current_user

        nav_items = [
            {"href": url_for("main.support"), "text": "Ondersteuning", "active": self.is_selected("support")},
            {"href": url_for("main.guidance_features"), "text": "Functies", "active": self.is_selected("features")},
            # {"href": url_for("main.guidance_pricing"), "text": "Prijzen", "active": self.is_selected("pricing")},
            {
                "href": url_for("main.guidance_using_notify"),
                "text": "Gebruik van Notify",
                "active": self.is_selected("using-notify"),
            },
        ]

        if current_user.platform_admin:
            nav_items.append(
                {
                    "href": url_for("main.platform_admin_search"),
                    "text": "Platformbeheer",
                    "active": self.is_selected("platform-admin"),
                }
            )

        if current_user.is_authenticated:
            nav_items.append(
                {
                    "href": url_for("main.your_account"),
                    "text": "Uw account",
                    "active": self.is_selected("your-account"),
                }
            )
        else:
            nav_items.append(
                {"href": url_for("main.sign_in"), "text": "Inloggen", "active": self.is_selected("sign-in")}
            )

        return nav_items


class MainNavigation(Navigation):
    mapping = {
        "dashboard": {
            "conversation",
            "inbox",
            "monthly",
            "returned_letter_summary",
            "returned_letters",
            "service_dashboard",
            "unsubscribe_request_reports_summary",
            "unsubscribe_request_report",
            "download_unsubscribe_request_report",
            "create_unsubscribe_request_report",
            "template_usage",
            "view_notification",
            "view_notifications",
        },
        "templates": {
            "action_blocked",
            "add_service_template",
            "check_messages",
            "check_notification",
            "choose_from_contact_list",
            "choose_template",
            "choose_template_to_copy",
            "confirm_redact_template",
            "conversation_reply",
            "copy_template",
            "delete_service_template",
            "edit_service_template",
            "edit_template_postage",
            "letter_template_attach_pages",
            "letter_template_change_language",
            "letter_template_confirm_remove_welsh",
            "manage_template_folder",
            "send_messages",
            "send_one_off",
            "send_one_off_letter_address",
            "send_one_off_step",
            "send_one_off_to_myself",
            "no_cookie.send_test_preview",
            "set_sender",
            "set_template_sender",
            "view_template",
            "view_template_version",
            "view_template_versions",
            "rename_template",
        },
        "uploads": {
            "upload_contact_list",
            "check_contact_list",
            "save_contact_list",
            "contact_list",
            "delete_contact_list",
            "upload_letter",
            "uploaded_letter_preview",
            "uploaded_letters",
            "uploads",
            "view_job",
            "view_jobs",
        },
        "team-members": {
            "confirm_edit_user_email",
            "confirm_edit_user_mobile_number",
            "edit_user_email",
            "edit_user_mobile_number",
            "edit_user_permissions",
            "invite_user",
            "manage_users",
            "remove_user_from_service",
        },
        "usage": {
            "usage",
        },
        "settings": {
            "add_organisation_from_gp_service",
            "add_organisation_from_nhs_local_service",
            "branding_nhs",
            "branding_option_preview",
            "email_branding_choose_banner_colour",
            "email_branding_choose_banner_type",
            "email_branding_choose_logo",
            "email_branding_enter_government_identity_logo_text",
            "email_branding_govuk",
            "email_branding_options",
            "email_branding_request",
            "email_branding_request_government_identity_logo",
            "email_branding_set_alt_text",
            "email_branding_upload_logo",
            "estimate_usage",
            "letter_branding_options",
            "letter_branding_request",
            "link_service_to_organisation",
            "request_to_go_live",
            "service_add_email_reply_to",
            "service_add_letter_contact",
            "service_add_sms_sender",
            "service_agreement",
            "service_accept_agreement",
            "service_confirm_agreement",
            "service_confirm_delete_email_reply_to",
            "service_confirm_delete_letter_contact",
            "service_confirm_delete_sms_sender",
            "service_edit_email_reply_to",
            "service_edit_letter_contact",
            "service_edit_sms_sender",
            "service_email_reply_to",
            "service_email_sender_change",
            "service_letter_contact_details",
            "service_make_blank_default_letter_contact",
            "service_name_change",
            "service_preview_branding",
            "service_receive_text_messages",
            "service_receive_text_messages_start",
            "service_receive_text_messages_stop",
            "service_receive_text_messages_stop_success",
            "service_set_auth_type",
            "service_set_channel",
            "send_files_by_email_contact_details",
            "service_set_branding",
            "service_set_inbound_number",
            "service_set_international_letters",
            "service_set_international_sms",
            "service_set_letters",
            "service_set_reply_to_email",
            "service_set_sms_prefix",
            "service_verify_reply_to_address",
            "service_settings",
            "service_sms_senders",
            "set_free_sms_allowance",
            "set_per_day_international_sms_message_limit",
            "set_per_day_message_limit",
            "set_per_minute_rate_limit",
            "submit_request_to_go_live",
        },
        "api-integration": {
            "api_callbacks",
            "api_documentation",
            "api_integration",
            "api_keys",
            "create_api_key",
            "delivery_status_callback",
            "received_text_messages_callback",
            "returned_letters_callback",
            "revoke_api_key",
            "guest_list",
            "old_guest_list",
        },
        "make-service-live": {
            "org_member_make_service_live_start",
            "org_member_make_service_live_service_name",
            "org_member_make_service_live_check_unique",
            "org_member_make_service_live_contact_user",
        },
    }


class CaseworkNavigation(Navigation):
    mapping = {
        "send-one-off": {
            "choose_from_contact_list",
            "choose_template",
            "send_one_off",
            "send_one_off_letter_address",
            "send_one_off_step",
            "send_one_off_to_myself",
        },
        "sent-messages": {
            "view_notifications",
            "view_notification",
        },
        "uploads": {
            "view_jobs",
            "view_job",
            "upload_contact_list",
            "check_contact_list",
            "save_contact_list",
            "contact_list",
            "delete_contact_list",
            "upload_letter",
            "uploaded_letter_preview",
            "uploaded_letters",
            "uploads",
        },
    }


class OrgNavigation(Navigation):
    mapping = {
        "dashboard": {
            "organisation_dashboard",
        },
        "settings": {
            "archive_organisation",
            "add_organisation_email_branding_options",
            "add_organisation_letter_branding_options",
            "edit_organisation_agreement",
            "edit_organisation_billing_details",
            "edit_organisation_can_approve_own_go_live_requests",
            "edit_organisation_crown_status",
            "edit_organisation_domains",
            "edit_organisation_go_live_notes",
            "edit_organisation_name",
            "edit_organisation_notes",
            "edit_organisation_type",
            "organisation_email_branding",
            "organisation_letter_branding",
            "organisation_settings",
        },
        "team-members": {
            "edit_organisation_user",
            "invite_org_user",
            "manage_org_users",
            "remove_user_from_organisation",
        },
        "trial-services": {
            "organisation_trial_mode_services",
        },
        "billing": {
            "organisation_billing",
        },
    }


class PlatformAdminNavigation(Navigation):
    mapping = {
        "search": {
            "platform_admin_search",
        },
        "organisations": {
            "organisations",
        },
        "providers": {
            "view_providers",
            "edit_sms_provider_ratio",
        },
        "reports": {
            "platform_admin_reports",
            "notifications_sent_by_service",
            "get_billing_report",
            "get_dvla_billing_report",
            "get_volumes_by_service",
            "get_daily_volumes",
            "get_daily_sms_provider_volumes",
            "platform_admin_users_list",
        },
        "email-branding": {
            "email_branding",
            "platform_admin_view_email_branding",
            "platform_admin_update_email_branding",
            "platform_admin_create_email_branding",
            "create_email_branding_government_identity_logo",
            "create_email_branding_government_identity_colour",
        },
        "letter-branding": {
            "letter_branding",
            "platform_admin_view_letter_branding",
            "create_letter_branding",
            "update_letter_branding",
        },
        "inbound-sms-numbers": {
            "inbound_sms_admin",
        },
        "email-complaints": {
            "platform_admin_list_complaints",
        },
        "returned-letters": {
            "platform_admin_returned_letters",
        },
        "clear-cache": {
            "clear_cache",
        },
    }

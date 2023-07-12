import pytest
from flask import Flask, url_for

from app import create_app
from app.navigation import (
    CaseworkNavigation,
    HeaderNavigation,
    MainNavigation,
    Navigation,
    OrgNavigation,
)
from tests.conftest import ORGANISATION_ID, SERVICE_ONE_ID, normalize_spaces

EXCLUDED_ENDPOINTS = set(
    map(
        Navigation.get_endpoint_with_blueprint,
        {
            "accept_invite",
            "accept_org_invite",
            "accessibility_statement",
            "action_blocked",
            "add_data_retention",
            "add_organisation_email_branding_options",
            "add_organisation_from_gp_service",
            "add_organisation_from_nhs_local_service",
            "add_organisation_letter_branding_options",
            "add_organisation",
            "add_service_template",
            "add_service",
            "api_callbacks",
            "api_documentation",
            "api_integration",
            "api_keys",
            "approve_broadcast_message",
            "archive_organisation",
            "archive_service",
            "archive_user",
            "bat_phone",
            "begin_tour",
            "branding_option_preview",
            "branding_nhs",
            "broadcast_dashboard_previous",
            "broadcast_dashboard_rejected",
            "broadcast_dashboard",
            "broadcast_tour_live",
            "broadcast_tour",
            "broadcast",
            "cancel_broadcast_message",
            "cancel_invited_org_user",
            "cancel_invited_user",
            "cancel_job",
            "cancel_letter_job",
            "cancel_letter",
            "change_user_auth",
            "check_and_resend_text_code",
            "check_and_resend_verification_code",
            "check_contact_list",
            "check_messages",
            "check_notification",
            "check_tour_notification",
            "choose_account",
            "choose_broadcast_area",
            "choose_broadcast_library",
            "choose_broadcast_sub_area",
            "choose_from_contact_list",
            "choose_service",
            "choose_template_to_copy",
            "choose_template",
            "clear_cache",
            "confirm_edit_user_email",
            "confirm_edit_user_mobile_number",
            "confirm_redact_template",
            "contact_list",
            "conversation_reply_with_template",
            "conversation_reply",
            "conversation",
            "cookies",
            "copy_template",
            "count_content_length",
            "create_api_key",
            "create_email_branding_government_identity_colour",
            "create_email_branding_government_identity_logo",
            "create_letter_branding",
            "data_retention",
            "delete_contact_list",
            "delete_service_template",
            "delete_template_folder",
            "delivery_status_callback",
            "design_content",
            "download_contact_list",
            "download_notifications_csv",
            "download_organisation_usage_report",
            "edit_data_retention",
            "edit_organisation_agreement",
            "edit_organisation_billing_details",
            "edit_organisation_can_approve_own_go_live_requests",
            "edit_organisation_can_ask_to_join_a_service",
            "edit_organisation_crown_status",
            "edit_organisation_domains",
            "edit_organisation_go_live_notes",
            "edit_organisation_name",
            "edit_organisation_notes",
            "edit_organisation_type",
            "edit_organisation_user",
            "edit_service_billing_details",
            "edit_service_notes",
            "edit_service_template",
            "edit_sms_provider_ratio",
            "edit_template_postage",
            "edit_user_email",
            "edit_user_mobile_number",
            "edit_user_permissions",
            "email_branding_choose_banner_colour",
            "email_branding_choose_banner_type",
            "email_branding_choose_logo",
            "email_branding_enter_government_identity_logo_text",
            "email_branding_govuk",
            "email_branding_options",
            "email_branding_request_government_identity_logo",
            "email_branding_request",
            "email_branding_set_alt_text",
            "email_branding_upload_logo",
            "email_branding",
            "email_not_received",
            "email_template",
            "error",
            "estimate_usage",
            "feedback",
            "forgot_password",
            "get_billing_report",
            "get_daily_sms_provider_volumes",
            "get_daily_volumes",
            "get_dvla_billing_report",
            "get_example_csv",
            "get_volumes_by_service",
            "go_to_dashboard_after_tour",
            "guest_list",
            "guidance_api_documentation",
            "guidance_billing_details",
            "guidance_bulk_sending",
            "guidance_delivery_times",
            "guidance_email_branding",
            "guidance_features",
            "guidance_formatting",
            "guidance_how_to_pay",
            "guidance_letter_branding",
            "guidance_links_and_URLs",
            "guidance_message_status",
            "guidance_optional_content",
            "guidance_personalisation",
            "guidance_pricing_letters",
            "guidance_pricing_text_messages",
            "guidance_pricing",
            "guidance_receive_text_messages",
            "guidance_reply_to_email_address",
            "guidance_roadmap",
            "guidance_schedule_messages",
            "guidance_security",
            "guidance_send_files_by_email",
            "guidance_team_members_and_permissions",
            "guidance_templates",
            "guidance_text_message_sender",
            "guidance_trial_mode",
            "guidance_upload_a_letter",
            "guidance_using_notify",
            "guidance_who_can_use_notify",
            "history",
            "inbound_sms_admin",
            "inbox_download",
            "inbox",
            "index",
            "invite_org_user",
            "invite_user",
            "json_updates.broadcast_dashboard_updates",
            "json_updates.conversation_updates",
            "json_updates.get_notifications_page_partials_as_json",
            "json_updates.inbox_updates",
            "json_updates.service_dashboard_updates",
            "json_updates.service_verify_reply_to_address_updates",
            "json_updates.view_job_updates",
            "json_updates.view_notification_updates",
            "letter_branding_options",
            "letter_branding_request",
            "letter_branding_set_name",
            "letter_branding_upload_branding",
            "letter_branding",
            "letter_spec",
            "letter_template",
            "letter_template_attach_pages",
            "letter_template_edit_pages",
            "link_service_to_organisation",
            "live_services_csv",
            "live_services",
            "main.redirects.historical_redirects",
            "make_service_live",
            "manage_org_users",
            "manage_template_folder",
            "manage_users",
            "monthly",
            "new_broadcast",
            "new_password",
            "no_cookie.check_messages_preview",
            "no_cookie.check_notification_preview",
            "no_cookie.letter_branding_preview_image",
            "no_cookie.send_test_preview",
            "no_cookie.view_letter_attachment_preview",
            "no_cookie.view_letter_template_preview",
            "no_cookie.view_template_version_preview",
            "notifications_sent_by_service",
            "old_guest_list",
            "old_letter_branding_option_preview",
            "old_service_dashboard",
            "organisation_billing",
            "organisation_dashboard",
            "organisation_download_agreement",
            "organisation_email_branding",
            "organisation_letter_branding",
            "organisation_settings",
            "organisation_trial_mode_services",
            "organisations",
            "performance",
            "platform_admin_archive_email_branding",
            "platform_admin_confirm_archive_email_branding",
            "platform_admin_create_email_branding",
            "platform_admin_list_complaints",
            "platform_admin_reports",
            "platform_admin_returned_letters",
            "platform_admin_search",
            "platform_admin_update_email_branding",
            "platform_admin_view_email_branding",
            "platform_admin_view_letter_branding",
            "platform_admin",
            "preview_broadcast_areas",
            "preview_broadcast_message",
            "privacy",
            "public_agreement",
            "public_download_agreement",
            "received_text_messages_callback",
            "redact_template",
            "redirect_old_search_pages",
            "register_from_invite",
            "register_from_org_invite",
            "register",
            "registration_continue",
            "reject_broadcast_message",
            "remove_broadcast_area",
            "remove_user_from_organisation",
            "remove_user_from_service",
            "request_to_go_live",
            "resend_email_link",
            "resend_email_verification",
            "returned_letter_summary",
            "returned_letters_report",
            "returned_letters",
            "revalidate_email_sent",
            "revoke_api_key",
            "save_contact_list",
            "security_policy",
            "send_files_by_email_contact_details",
            "send_from_contact_list",
            "send_messages",
            "send_notification",
            "send_one_off_letter_address",
            "send_one_off_step",
            "send_one_off_to_myself",
            "send_one_off",
            "send_uploaded_letter",
            "service_accept_agreement",
            "service_add_email_reply_to",
            "service_add_letter_contact",
            "service_add_sms_sender",
            "service_agreement",
            "service_confirm_agreement",
            "service_confirm_broadcast_account_type",
            "service_confirm_delete_email_reply_to",
            "service_confirm_delete_letter_contact",
            "service_confirm_delete_sms_sender",
            "service_confirm_disable_email_auth",
            "service_dashboard",
            "service_delete_email_reply_to",
            "service_delete_letter_contact",
            "service_delete_sms_sender",
            "service_download_agreement",
            "service_edit_email_reply_to",
            "service_edit_letter_contact",
            "service_edit_sms_sender",
            "service_email_reply_to",
            "service_letter_contact_details",
            "service_make_blank_default_letter_contact",
            "service_name_change",
            "service_preview_branding",
            "service_receive_text_messages_start",
            "service_receive_text_messages_stop",
            "service_receive_text_messages",
            "service_set_auth_type_for_users",
            "service_set_auth_type",
            "service_set_branding_add_to_branding_pool_step",
            "service_set_branding",
            "service_set_broadcast_channel",
            "service_set_broadcast_network",
            "service_set_channel",
            "service_set_inbound_number",
            "service_set_international_letters",
            "service_set_international_sms",
            "service_set_letters",
            "service_set_permission",
            "service_set_reply_to_email",
            "service_set_sms_prefix",
            "service_settings",
            "service_sms_senders",
            "service_switch_count_as_live",
            "service_switch_live",
            "service_verify_reply_to_address",
            "services_or_dashboard",
            "set_free_sms_allowance",
            "set_per_day_message_limit",
            "set_per_minute_rate_limit",
            "set_sender",
            "set_template_sender",
            "show_accounts_or_dashboard",
            "sign_in",
            "sign_out",
            "start_job",
            "submit_request_to_go_live",
            "support_public",
            "support",
            "template_history",
            "template_usage",
            "terms_of_use",
            "thanks",
            "tour_step",
            "triage",
            "trial_services",
            "two_factor_email_interstitial",
            "two_factor_email_sent",
            "two_factor_email",
            "two_factor_sms",
            "two_factor_webauthn",
            "update_letter_branding",
            "upload_contact_list",
            "upload_letter",
            "uploaded_letter_preview",
            "uploaded_letters",
            "uploads",
            "usage",
            "user_information",
            "user_profile",
            "user_profile_confirm_delete_mobile_number",
            "user_profile_confirm_delete_security_key",
            "user_profile_delete_security_key",
            "user_profile_disable_platform_admin_view",
            "user_profile_email_authenticate",
            "user_profile_email_confirm",
            "user_profile_email",
            "user_profile_manage_security_key",
            "user_profile_mobile_number_authenticate",
            "user_profile_mobile_number_confirm",
            "user_profile_mobile_number_delete",
            "user_profile_mobile_number",
            "user_profile_name",
            "user_profile_password",
            "user_profile_security_keys",
            "user_profile_take_part_in_user_research",
            "verify_email",
            "verify",
            "view_current_broadcast",
            "view_job_csv",
            "view_job",
            "view_jobs",
            "view_letter_notification_as_preview",
            "view_letter_upload_as_preview",
            "view_notification",
            "view_notifications",
            "view_previous_broadcast",
            "view_provider",
            "view_providers",
            "view_rejected_broadcast",
            "view_template_version",
            "view_template_versions",
            "view_template",
            "webauthn_begin_authentication",
            "webauthn_begin_register",
            "webauthn_complete_authentication",
            "webauthn_complete_register",
            "write_new_broadcast",
        },
    )
)


def flask_app():
    app = Flask("app")
    create_app(app)

    ctx = app.app_context()
    ctx.push()

    yield app


all_endpoints = set(rule.endpoint for rule in next(flask_app()).url_map.iter_rules())

navigation_instances = (
    MainNavigation(),
    HeaderNavigation(),
    OrgNavigation(),
    CaseworkNavigation(),
)


@pytest.mark.parametrize(
    "navigation_instance", navigation_instances, ids=(x.__class__.__name__ for x in navigation_instances)
)
def test_navigation_items_are_properly_defined(navigation_instance):
    for endpoint in navigation_instance.endpoints_with_navigation:
        assert endpoint in all_endpoints, "{} is not a real endpoint (in {}.mapping)".format(
            endpoint, type(navigation_instance).__name__
        )
        assert (
            navigation_instance.endpoints_with_navigation.count(endpoint) == 1
        ), f"{endpoint} found more than once in {type(navigation_instance).__name__}.mapping"


def test_excluded_endpoints_are_all_found_in_app():
    extra_excluded_endpoints = EXCLUDED_ENDPOINTS - all_endpoints
    assert not extra_excluded_endpoints


@pytest.mark.parametrize(
    "navigation_instance", navigation_instances, ids=(x.__class__.__name__ for x in navigation_instances)
)
def test_all_endpoints_are_covered(navigation_instance):
    covered_endpoints = (
        set(navigation_instance.endpoints_with_navigation)
        | EXCLUDED_ENDPOINTS
        | {"static", "status.show_status", "metrics"}
    )
    uncovered_endpoints = all_endpoints - covered_endpoints
    assert not uncovered_endpoints


@pytest.mark.parametrize(
    "navigation_instance", navigation_instances, ids=(x.__class__.__name__ for x in navigation_instances)
)
@pytest.mark.xfail(raises=KeyError)
def test_raises_on_invalid_navigation_item(client_request, navigation_instance):
    navigation_instance.is_selected("foo")


@pytest.mark.parametrize(
    "endpoint, selected_nav_item",
    [
        ("main.choose_template", "Templates"),
        ("main.manage_users", "Team members"),
    ],
)
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
    selected_nav_items = page.select(".navigation a.selected")
    assert len(selected_nav_items) == 1
    assert selected_nav_items[0].text.strip() == selected_nav_item


@pytest.mark.parametrize(
    "endpoint, selected_nav_item",
    [
        ("main.guidance_pricing", "Pricing"),
        ("main.support", "Support"),
    ],
)
def test_a_page_should_have_selected_header_navigation_item(
    client_request,
    endpoint,
    selected_nav_item,
):
    page = client_request.get(endpoint, service_id=SERVICE_ONE_ID)
    selected_nav_items = page.select(".govuk-header__navigation-item--active")
    assert len(selected_nav_items) == 1
    assert selected_nav_items[0].text.strip() == selected_nav_item


@pytest.mark.parametrize(
    "endpoint, selected_nav_item",
    [
        ("main.organisation_dashboard", "Usage"),
        ("main.manage_org_users", "Team members"),
    ],
)
def test_a_page_should_nave_selected_org_navigation_item(
    client_request,
    mock_get_organisation,
    mock_get_users_for_organisation,
    mock_get_invited_users_for_organisation,
    endpoint,
    selected_nav_item,
    mocker,
):
    mocker.patch("app.organisations_client.get_services_and_usage", return_value={"services": [], "updated_at": None})
    page = client_request.get(endpoint, org_id=ORGANISATION_ID)
    selected_nav_items = page.select(".navigation a.selected")
    assert len(selected_nav_items) == 1
    assert selected_nav_items[0].text.strip() == selected_nav_item


def test_navigation_urls(
    client_request,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_api_keys,
):
    page = client_request.get("main.choose_template", service_id=SERVICE_ONE_ID)
    assert [a["href"] for a in page.select(".navigation a")] == [
        f"/services/{SERVICE_ONE_ID}",
        f"/services/{SERVICE_ONE_ID}/templates",
        f"/services/{SERVICE_ONE_ID}/uploads",
        f"/services/{SERVICE_ONE_ID}/users",
        f"/services/{SERVICE_ONE_ID}/usage",
        f"/services/{SERVICE_ONE_ID}/service-settings",
        f"/services/{SERVICE_ONE_ID}/api",
    ]


def test_navigation_for_services_with_broadcast_permission(
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_api_keys,
    active_user_create_broadcasts_permission,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)

    page = client_request.get("main.choose_template", service_id=SERVICE_ONE_ID)
    assert [a["href"] for a in page.select(".navigation a")] == [
        f"/services/{SERVICE_ONE_ID}/current-alerts",
        f"/services/{SERVICE_ONE_ID}/past-alerts",
        f"/services/{SERVICE_ONE_ID}/rejected-alerts",
        f"/services/{SERVICE_ONE_ID}/templates",
        f"/services/{SERVICE_ONE_ID}/users",
    ]


def test_navigation_for_services_with_broadcast_permission_platform_admin(
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_api_keys,
    platform_admin_user,
):
    service_one["permissions"] += ["broadcast"]

    client_request.login(platform_admin_user)
    page = client_request.get("main.choose_template", service_id=SERVICE_ONE_ID)
    assert [a["href"] for a in page.select(".navigation a")] == [
        f"/services/{SERVICE_ONE_ID}/current-alerts",
        f"/services/{SERVICE_ONE_ID}/past-alerts",
        f"/services/{SERVICE_ONE_ID}/rejected-alerts",
        f"/services/{SERVICE_ONE_ID}/templates",
        f"/services/{SERVICE_ONE_ID}/users",
        f"/services/{SERVICE_ONE_ID}/service-settings",
        f"/services/{SERVICE_ONE_ID}/api/keys",
    ]


def test_caseworkers_get_caseworking_navigation(
    client_request,
    mock_get_template_folders,
    mock_get_service_templates,
    mock_has_no_jobs,
    mock_get_api_keys,
    active_caseworking_user,
):
    client_request.login(active_caseworking_user)
    page = client_request.get("main.choose_template", service_id=SERVICE_ONE_ID)
    assert normalize_spaces(page.select_one("header + .govuk-width-container nav").text) == (
        "Templates Sent messages Uploads Team members"
    )


def test_caseworkers_see_jobs_nav_if_jobs_exist(
    client_request,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_has_jobs,
    active_caseworking_user,
    mock_get_api_keys,
):
    client_request.login(active_caseworking_user)
    page = client_request.get("main.choose_template", service_id=SERVICE_ONE_ID)
    assert normalize_spaces(page.select_one("header + .govuk-width-container nav").text) == (
        "Templates Sent messages Uploads Team members"
    )


def test_make_service_live_link_is_shown_in_limited_circumstances(
    client_request,
    service_one,
    platform_admin_user,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_api_keys,
    mock_get_organisation,
    fake_uuid,
):
    service_one["has_active_go_live_request"] = True
    service_one["organisation"] = fake_uuid

    client_request.login(platform_admin_user)

    page = client_request.get("main.choose_template", service_id=SERVICE_ONE_ID)

    last_navigation_item = page.select(".navigation li")[-1]

    assert last_navigation_item["class"] == ["navigation__item", "navigation__item--with-separator"]
    assert normalize_spaces(last_navigation_item.text) == "Make service live"
    assert last_navigation_item.select_one("a")["href"] == url_for(
        "main.make_service_live",
        service_id=SERVICE_ONE_ID,
    )

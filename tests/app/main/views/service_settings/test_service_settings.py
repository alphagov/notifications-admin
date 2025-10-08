from datetime import datetime
from functools import partial
from unittest.mock import Mock, PropertyMock, call
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4

import pytest
from flask import g, url_for
from freezegun import freeze_time
from notifications_python_client.errors import HTTPError

import app
from app.constants import SIGN_IN_METHOD_TEXT, SIGN_IN_METHOD_TEXT_OR_EMAIL
from app.main.views_nl.service_settings.branding import (
    _should_set_default_org_email_branding,
)
from app.models.service import Service
from tests import (
    find_element_by_tag_and_partial_text,
    organisation_json,
    sample_uuid,
    service_json,
    validate_route_permission,
)
from tests.conftest import (
    ORGANISATION_ID,
    SERVICE_ONE_ID,
    TEMPLATE_ONE_ID,
    USER_ONE_ID,
    create_active_user_no_settings_permission,
    create_active_user_with_permissions,
    create_letter_contact_block,
    create_multiple_email_reply_to_addresses,
    create_multiple_letter_contact_blocks,
    create_multiple_sms_senders,
    create_platform_admin_user,
    create_reply_to_email_address,
    create_service_one_user,
    create_sms_sender,
    normalize_spaces,
)

FAKE_TEMPLATE_ID = uuid4()


@pytest.mark.skip(reason="[NOTIFYNL] email_domains.txt change breaks this.")
@pytest.mark.parametrize(
    "user, service_permissions, expected_rows",
    [
        (
            create_active_user_with_permissions(),
            ["sms", "email"],
            [
                "Service name Test Service Change service name",
                "Sign-in method Text message code Change sign-in method",
                "Data retention period 7 days Change data retention",
                "Send emails On Change your settings for sending emails",
                "Email sender name Test Service test.service@notifications.service.gov.uk Change email sender name",
                "Reply-to email addresses Not set Manage reply-to email addresses",
                "Email branding GOV.UK Change email branding",
                "Send files by email contact_us@gov.uk Manage sending files by email",
                "Email limit 1,000 per day 1,234 sent today Change daily email limit",
                "Send text messages On Change your settings for sending text messages",
                "Text message sender IDs GOVUK Manage text message sender IDs",
                "Start text messages with service name On Change your settings for starting text messages with service name",  # noqa
                "Receive text messages Off Change your settings for receiving text messages",
                "Text message limit 1,000 per day 1,234 sent today Change daily text message limit",
                "Send international text messages Off Change your settings for sending international text messages",
                "Send letters Off Change your settings for sending letters",
            ],
        ),
        (
            create_active_user_with_permissions(),
            ["letter"],
            [
                "Service name Test Service Change service name",
                "Sign-in method Text message code Change sign-in method",
                "Data retention period 7 days Change data retention",
                "Send emails Off Change your settings for sending emails",
                "Send text messages Off Change your settings for sending text messages",
                "Send letters On Change your settings for sending letters",
                "Send international letters Off Change your settings for sending international letters",
                "Sender addresses Not set Manage sender addresses",
                "Letter branding Not set Change letter branding",
                "Letter limit 1,000 per day 1,234 sent today Change daily letter limit",
            ],
        ),
        (
            create_active_user_no_settings_permission(),
            ["sms", "email", "letter"],
            [
                "Service name Test Service",
                "Sign-in method Text message code",
                "Data retention period 7 days",
                "Send emails On",
                "Email sender name Test Service test.service@notifications.service.gov.uk",
                "Reply-to email addresses Not set Manage reply-to email addresses",  # user will see manage button
                "Email branding GOV.UK",
                "Send files by email contact_us@gov.uk",
                "Email limit 1,000 per day 1,234 sent today",
                "Send text messages On",
                "Text message sender IDs GOVUK Manage text message sender IDs",  # user will see manage button
                "Start text messages with service name On",
                "Receive text messages Off",
                "Text message limit 1,000 per day 1,234 sent today",
                "Send international text messages Off",
                "Send letters On",
                "Send international letters Off",
                "Sender addresses Not set Manage sender addresses",  # user will see manage button
                "Letter branding Not set",
                "Letter limit 1,000 per day 1,234 sent today",
            ],
        ),
        (
            create_platform_admin_user(),
            ["sms", "email"],
            [
                "Service name Test Service Change service name",
                "Sign-in method Text message code Change sign-in method",
                "Data retention period 7 days Change data retention",
                "Send emails On Change your settings for sending emails",
                "Email sender name Test Service test.service@notifications.service.gov.uk Change email sender name",
                "Reply-to email addresses Not set Manage reply-to email addresses",
                "Email branding GOV.UK Change email branding",
                "Send files by email contact_us@gov.uk Manage sending files by email",
                "Email limit 1,000 per day 1,234 sent today Change daily email limit",
                "Send text messages On Change your settings for sending text messages",
                "Text message sender IDs GOVUK Manage text message sender IDs",
                "Start text messages with service name On Change your settings for starting text messages with service name",  # noqa
                "Receive text messages Off Change your settings for receiving text messages",
                "Text message limit 1,000 per day 1,234 sent today Change daily text message limit",
                "Send international text messages Off Change your settings for sending international text messages",
                "Send letters Off Change your settings for sending letters",
                "Live On Change service status",
                "Count in list of live services Yes Change if service is counted in list of live services",
                "Billing details None Change billing details for service",
                "Notes None Change the notes for the service",
                "Organisation Test organisation Central government Change organisation for service",
                "Rate limit 3,000 per minute Change rate limit",
                "Email limit 1,000 per day Change daily email limit",
                "Text message limit 1,000 per day Change daily text message limit",
                "Letter limit 1,000 per day Change daily letter limit",
                "Free text message allowance 250,000 per year Change free text message allowance",
                "Email branding GOV.UK Change email branding (admin view)",
                "Letter branding Not set Change letter branding (admin view)",
                "Custom data retention Email – 7 days Change data retention",
                "Receive inbound SMS Off Change your settings for Receive inbound SMS",
                "Email authentication Off Change your settings for Email authentication",
                "Sending SMS to UK landlines Off Change your settings for Sending SMS to UK landlines",
            ],
        ),
        (
            create_platform_admin_user(),
            ["letter"],
            [
                "Service name Test Service Change service name",
                "Sign-in method Text message code Change sign-in method",
                "Data retention period 7 days Change data retention",
                "Send emails Off Change your settings for sending emails",
                "Send text messages Off Change your settings for sending text messages",
                "Send letters On Change your settings for sending letters",
                "Send international letters Off Change your settings for sending international letters",
                "Sender addresses Not set Manage sender addresses",
                "Letter branding Not set Change letter branding",
                "Letter limit 1,000 per day 1,234 sent today Change daily letter limit",
                "Live On Change service status",
                "Count in list of live services Yes Change if service is counted in list of live services",
                "Billing details None Change billing details for service",
                "Notes None Change the notes for the service",
                "Organisation Test organisation Central government Change organisation for service",
                "Rate limit 3,000 per minute Change rate limit",
                "Email limit 1,000 per day Change daily email limit",
                "Text message limit 1,000 per day Change daily text message limit",
                "Letter limit 1,000 per day Change daily letter limit",
                "Free text message allowance 250,000 per year Change free text message allowance",
                "Email branding GOV.UK Change email branding (admin view)",
                "Letter branding Not set Change letter branding (admin view)",
                "Custom data retention Email – 7 days Change data retention",
                "Email authentication Off Change your settings for Email authentication",
                "Sending SMS to UK landlines Off Change your settings for Sending SMS to UK landlines",
            ],
        ),
    ],
)
def test_service_settings_page_visible_settings_depend_on_user_and_service_permissions(
    client_request,
    mocker,
    api_user_active,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    user,
    service_permissions,
    expected_rows,
    mock_get_service_settings_page_common,
):
    service_one = service_json(
        SERVICE_ONE_ID,
        users=[api_user_active["id"]],
        permissions=service_permissions,
        organisation_id=ORGANISATION_ID,
        contact_link="contact_us@gov.uk",
        restricted=False,
    )
    mocker.patch("app.service_api_client.get_service", return_value={"data": service_one})
    mocker.patch("app.service_api_client.get_notification_count", return_value=1_234)

    client_request.login(user, service_one)
    page = client_request.get("main.service_settings", service_id=SERVICE_ONE_ID)

    assert page.select_one("h1").text == "Settings"
    rows = page.select(".govuk-summary-list__row")
    assert len(rows) == len(expected_rows)
    assert [" ".join(row.text.split()) for row in rows] == expected_rows
    app.service_api_client.get_service.assert_called_with(SERVICE_ONE_ID)


@pytest.mark.parametrize(
    "endpoint",
    [
        "main.service_sms_senders",
        "main.service_settings",
        "main.service_email_reply_to",
        "main.service_letter_contact_details",
    ],
)
def test_user_with_manage_api_keys_permission_but_no_settings_permission_can_view_certain_settings_pages(
    client_request,
    service_one,
    active_user_no_settings_permission,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    single_sms_sender,
    mocker,
    endpoint,
):
    mocker.patch("app.models.user.Users._get_items", return_value=[active_user_no_settings_permission])
    mocker.patch("app.service_api_client.get_notification_count", return_value=1_234)
    mocker.patch("app.service_api_client.get_service", return_value={"data": service_one})
    mocker.patch(
        "app.service_api_client.get_service_data_retention",
        return_value=[],
    )

    client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        branding_type="letter",
        _expected_status=200,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_shows_individual_data_retentions_if_different(
    client_request,
    mocker,
    api_user_active,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    mock_get_service_settings_page_common,
):
    user = create_platform_admin_user()
    service_one = service_json(
        SERVICE_ONE_ID,
        users=[api_user_active["id"]],
        permissions=[],
        organisation_id=ORGANISATION_ID,
        contact_link="contact_us@gov.uk",
    )
    mocker.patch("app.service_api_client.get_service", return_value={"data": service_one})
    mocker.patch(
        "app.service_api_client.get_service_data_retention",
        return_value=[
            {
                "id": str(sample_uuid()),
                "service_id": str(sample_uuid()),
                "service_name": "service name",
                "notification_type": "email",
                "days_of_retention": 3,
                "created_at": datetime.now(),
                "updated_at": None,
            }
        ],
    )

    client_request.login(user, service_one)
    page = client_request.get("main.service_settings", service_id=SERVICE_ONE_ID)

    assert (
        "Data retention period Email – 3 days Text message – 7 days Letter – 7 days Change data retention"
        in normalize_spaces(page.text)
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_no_go_live_link_for_service_without_organisation(
    client_request,
    mocker,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    platform_admin_user,
    mock_get_service_settings_page_common,
):
    mocker.patch("app.organisations_client.get_organisation", return_value=None)
    client_request.login(platform_admin_user)
    page = client_request.get("main.service_settings", service_id=SERVICE_ONE_ID)

    assert page.select_one("h1").text == "Settings"

    is_live = find_element_by_tag_and_partial_text(page, tag="dt", string="Live")
    assert normalize_spaces(is_live.find_next_sibling().text) == "No Organisation must be set first"

    organisation = find_element_by_tag_and_partial_text(page, tag="dt", string="Organisation")
    assert normalize_spaces(organisation.find_next_siblings()[0].text) == "Not set Central government"
    assert normalize_spaces(organisation.find_next_siblings()[1].text) == "Change organisation for service"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_organisation_name_links_to_org_dashboard(
    client_request,
    platform_admin_user,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    mock_get_service_settings_page_common,
    mocker,
):
    service_one = service_json(SERVICE_ONE_ID, permissions=["sms", "email"], organisation_id=ORGANISATION_ID)
    mocker.patch("app.service_api_client.get_service", return_value={"data": service_one})

    client_request.login(platform_admin_user, service_one)
    response = client_request.get("main.service_settings", service_id=SERVICE_ONE_ID)

    org_row = find_element_by_tag_and_partial_text(response, tag="dt", string="Organisation").parent
    assert org_row.find("a")["href"] == url_for("main.organisation_dashboard", org_id=ORGANISATION_ID)
    assert normalize_spaces(org_row.find("a").text) == "Test organisation"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "service_contact_link,expected_text",
    [
        ("contact.me@gov.uk", "Send files by email contact.me@gov.uk Manage sending files by email"),
        (None, "Send files by email Not set up Manage sending files by email"),
    ],
)
def test_send_files_by_email_row_on_settings_page(
    client_request,
    platform_admin_user,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    mock_get_service_settings_page_common,
    mocker,
    service_contact_link,
    expected_text,
):
    service_one = service_json(
        SERVICE_ONE_ID, permissions=["sms", "email"], organisation_id=ORGANISATION_ID, contact_link=service_contact_link
    )

    mocker.patch("app.service_api_client.get_service", return_value={"data": service_one})

    client_request.login(platform_admin_user, service_one)
    response = client_request.get("main.service_settings", service_id=SERVICE_ONE_ID)

    org_row = find_element_by_tag_and_partial_text(
        response, tag=".govuk-summary-list__row", string="Send files by email"
    )
    assert normalize_spaces(org_row.get_text()) == expected_text


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "permissions, expected_rows",
    [
        (
            ["email", "sms", "inbound_sms", "international_sms"],
            [
                "Service name service one Change service name",
                "Sign-in method Text message code Change sign-in method",
                "Data retention period 7 days Change data retention",
                "Send emails On Change your settings for sending emails",
                "Email sender name service one service.one@notifications.service.gov.uk Change email sender name",
                "Reply-to email addresses test@example.com Manage reply-to email addresses",
                "Email branding Organisation name Change email branding",
                "Send files by email Not set up Manage sending files by email",
                "Email limit 1,000 per day 0 sent today Change daily email limit",
                "Send text messages On Change your settings for sending text messages",
                "Text message sender IDs GOVUK Manage text message sender IDs",
                "Start text messages with service name On Change your settings for starting text messages with service name",  # noqa
                "Receive text messages On Change your settings for receiving text messages",
                "Text message limit 1,000 per day 0 sent today Change daily text message limit",
                "Send international text messages On Change your settings for sending international text messages",
                "International text message limit 500 per day 0 sent today Change daily international text message limit",  # noqa
                "Send letters Off Change your settings for sending letters",
            ],
        ),
        (
            ["email", "sms", "email_auth"],
            [
                "Service name service one Change service name",
                "Sign-in method Email link or text message code Change sign-in method",
                "Data retention period 7 days Change data retention",
                "Send emails On Change your settings for sending emails",
                "Email sender name service one service.one@notifications.service.gov.uk Change email sender name",
                "Reply-to email addresses test@example.com Manage reply-to email addresses",
                "Email branding Organisation name Change email branding",
                "Send files by email Not set up Manage sending files by email",
                "Email limit 1,000 per day 0 sent today Change daily email limit",
                "Send text messages On Change your settings for sending text messages",
                "Text message sender IDs GOVUK Manage text message sender IDs",
                "Start text messages with service name On Change your settings for starting text messages with service name",  # noqa
                "Receive text messages Off Change your settings for receiving text messages",
                "Text message limit 1,000 per day 0 sent today Change daily text message limit",
                "Send international text messages Off Change your settings for sending international text messages",
                "Send letters Off Change your settings for sending letters",
            ],
        ),
        (
            ["letter"],
            [
                "Service name service one Change service name",
                "Sign-in method Text message code Change sign-in method",
                "Data retention period 7 days Change data retention",
                "Send emails Off Change your settings for sending emails",
                "Send text messages Off Change your settings for sending text messages",
                "Send letters On Change your settings for sending letters",
                "Send international letters Off Change your settings for sending international letters",
                "Sender addresses 1 Example Street Manage sender addresses",
                "Letter branding Not set Change letter branding",
                "Letter limit 1,000 per day 0 sent today Change daily letter limit",
            ],
        ),
    ],
)
def test_should_show_overview_for_service_with_more_things_set(
    client_request,
    active_user_with_permissions,
    mocker,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    single_sms_sender,
    mock_get_email_branding,
    mock_get_service_settings_page_common,
    permissions,
    expected_rows,
):
    client_request.login(active_user_with_permissions)
    service_one["permissions"] = permissions
    service_one["restricted"] = False
    service_one["email_branding"] = uuid4()
    page = client_request.get("main.service_settings", service_id=service_one["id"])
    assert [
        " ".join(row.text.split()) for row in page.select(".notify-summary-list .govuk-summary-list__row")[0:]
    ] == expected_rows


def test_if_cant_send_letters_then_cant_see_letter_contact_block(
    client_request,
    service_one,
    single_reply_to_email_address,
    no_letter_contact_blocks,
    single_sms_sender,
    mock_get_service_settings_page_common,
):
    response = client_request.get("main.service_settings", service_id=service_one["id"])
    assert "Letter contact block" not in response


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_letter_contact_block_shows_none_if_not_set(
    client_request,
    service_one,
    single_reply_to_email_address,
    no_letter_contact_blocks,
    single_sms_sender,
    mock_get_service_settings_page_common,
):
    service_one["permissions"] = ["letter"]
    page = client_request.get(
        "main.service_settings",
        service_id=SERVICE_ONE_ID,
    )

    div = page.select(".service-letter-settings .govuk-summary-list__value")[2]
    assert div.text.strip() == "Not set"
    assert "govuk-summary-list__value--default" in div.attrs["class"][1]


def test_escapes_letter_contact_block(
    client_request,
    service_one,
    mocker,
    single_reply_to_email_address,
    single_sms_sender,
    injected_letter_contact_block,
    mock_get_service_settings_page_common,
):
    service_one["permissions"] = ["letter"]
    page = client_request.get(
        "main.service_settings",
        service_id=SERVICE_ONE_ID,
    )
    div = str(page.select(".service-letter-settings .govuk-summary-list__value")[2])
    assert "foo<br/>bar" in div
    assert "<script>" not in div


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "organisation_type, expected_content_lines",
    [
        (
            "central",
            [
                "Your service name should tell the recipient what your message is about, as well as who it’s from. For example:",  # noqa
                "Register to vote",
            ],
        ),
        (
            "local",
            [
                "Your service name should tell the recipient what your message is about, as well as who it’s from. For example",  # noqa
                "School admissions - Test Organisation",
            ],
        ),
        ("nhs", ["Your service name should tell the recipient what your message is about, as well as who it’s from."]),
    ],
)
def test_change_service_name_content_varies_by_organisation_type(
    client_request, mocker, service_one, organisation_type, expected_content_lines
):
    mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=organisation_json(organisation_type=organisation_type),
    )
    service_one["organisation_type"] = organisation_type
    page = client_request.get("main.service_name_change", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Change your service name"
    assert page.select_one("input", attrs={"type": "text"})["value"] == "service one"
    assert all(content in page.select_one("main").text for content in expected_content_lines)
    app.service_api_client.get_service.assert_called_with(SERVICE_ONE_ID)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_service_org_in_hint_on_change_service_name_page_for_local_services_if_service_has_org(
    client_request,
    service_one,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=organisation_json(organisation_type="local"),
    )
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(organisation_type="local", name="Local Authority"),
    )
    service_one["organisation_type"] = "local"
    service_one["organisation"] = "1234"
    page = client_request.get("main.service_name_change", service_id=SERVICE_ONE_ID)
    # when there is organisation on the service object, it is used for hint text instead of user default org
    assert "School admissions - Local Authority" in page.select_one("ul.govuk-list.govuk-list--bullet").text


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_service_name_with_no_prefixing(
    client_request,
    service_one,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=organisation_json(organisation_type="nhs"),
    )
    service_one["organisation_type"] = "nhs"
    service_one["prefix_sms"] = False
    page = client_request.get("main.service_name_change", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Change your service name"
    assert (
        "Your service name should tell the recipient what your message is about, as well as who it’s from."
        in page.select_one("main").text
    )


@pytest.mark.parametrize(
    "name, error_message",
    [
        ("", "Error: Enter a service name"),
        (".", "Service name must include at least 2 letters or numbers"),
        ("GOV.UK Ειδοποίηση", "Service name cannot include characters from a non-Latin alphabet"),
        # under the 255 db col length, but when combined with normalised service name to make an email, it's too long
        ("a" * 150 + " " * 100 + "a", "Service name cannot be longer than 143 characters"),
    ],
)
def test_service_name_change_fails_if_new_name_fails_validation(
    client_request,
    mock_update_service,
    name,
    error_message,
):
    page = client_request.post(
        "main.service_name_change",
        service_id=SERVICE_ONE_ID,
        _data={"name": name},
        _expected_status=200,
    )
    assert not mock_update_service.called
    assert error_message in page.select_one(".govuk-error-message").text


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_show_limits_for_live_service(
    client_request,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    single_sms_sender,
    mock_get_service_settings_page_common,
):
    service_one["restricted"] = False
    service_one["email_message_limit"] = 1_000
    service_one["sms_message_limit"] = 2_000
    service_one["letter_message_limit"] = 3_000

    page = client_request.get(
        "main.service_settings",
        service_id=SERVICE_ONE_ID,
    )

    assert page.select_one("main > h2").text == "Your service is live"
    assert normalize_spaces(page.select_one("main p").text) == "To delete this service, contact us."


@pytest.mark.parametrize(
    "agreement_signed",
    (
        True,
        None,
        pytest.param(False, marks=pytest.mark.xfail),
    ),
)
@freeze_time("2017-04-01 11:09:00.061258")
def test_switch_service_to_live(
    client_request,
    platform_admin_user,
    mock_update_service,
    mock_get_inbound_number_for_service,
    mock_get_service_organisation,
    agreement_signed,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(agreement_signed=agreement_signed),
    )
    client_request.login(platform_admin_user)
    client_request.post(
        "main.service_switch_live",
        service_id=SERVICE_ONE_ID,
        _data={"enabled": "True"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_settings",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_update_service.assert_called_with(
        SERVICE_ONE_ID,
        email_message_limit=250_000,
        sms_message_limit=250_000,
        letter_message_limit=20_000,
        restricted=False,
        go_live_at="2017-04-01 11:09:00.061258",
        has_active_go_live_request=False,
    )


def test_switch_service_to_live_with_no_organisation(
    fake_uuid,
    client_request,
    platform_admin_user,
):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.service_switch_live",
        service_id=SERVICE_ONE_ID,
        _data={"enabled": "True"},
        _expected_status=403,
    )


@pytest.mark.parametrize(
    "active",
    (
        pytest.param(False),
        pytest.param(True, marks=pytest.mark.xfail(reason="403 caused by something else")),
    ),
)
def test_switch_archived_service_to_live(
    client_request,
    service_one,
    platform_admin_user,
    fake_uuid,
    active,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(agreement_signed=True),
    )
    service_one["organisation"] = fake_uuid
    service_one["active"] = active

    client_request.login(platform_admin_user)
    client_request.get(
        "main.service_switch_live",
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
    )
    client_request.post(
        "main.service_switch_live",
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_show_live_service(
    client_request,
    mock_get_live_service,
    single_reply_to_email_address,
    single_letter_contact_block,
    single_sms_sender,
    mock_get_service_settings_page_common,
):
    page = client_request.get(
        "main.service_settings",
        service_id=SERVICE_ONE_ID,
    )
    assert page.select_one("h1").text.strip() == "Settings"
    assert "Your service is in trial mode" not in page.text


def test_switch_service_to_restricted(
    client_request,
    platform_admin_user,
    mock_get_live_service,
    mock_update_service,
    mock_get_inbound_number_for_service,
):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.service_switch_live",
        service_id=SERVICE_ONE_ID,
        _data={"enabled": "False"},
        _expected_status=302,
        _expected_response=url_for(
            "main.service_settings",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_update_service.assert_called_with(
        SERVICE_ONE_ID,
        email_message_limit=50,
        sms_message_limit=50,
        letter_message_limit=50,
        restricted=True,
        go_live_at=None,
        has_active_go_live_request=False,
    )


@pytest.mark.parametrize(
    "count_as_live, selected, labelled",
    (
        (True, "True", "Yes"),
        (False, "False", "No"),
    ),
)
def test_show_switch_service_to_count_as_live_page(
    client_request,
    platform_admin_user,
    mock_update_service,
    count_as_live,
    selected,
    labelled,
    mocker,
):
    mocker.patch(
        "app.models.service.Service.count_as_live",
        create=True,
        new_callable=PropertyMock,
        return_value=count_as_live,
    )
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.service_switch_count_as_live",
        service_id=SERVICE_ONE_ID,
    )
    assert page.select_one("[checked]")["value"] == selected
    assert page.select_one(f"label[for={page.select_one('[checked]')['id']}]").text.strip() == labelled


@pytest.mark.parametrize(
    "post_data, expected_persisted_value",
    (
        ("True", True),
        ("False", False),
    ),
)
def test_switch_service_to_count_as_live(
    client_request,
    platform_admin_user,
    mock_update_service,
    post_data,
    expected_persisted_value,
):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.service_switch_count_as_live",
        service_id=SERVICE_ONE_ID,
        _data={"enabled": post_data},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_settings",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_update_service.assert_called_with(
        SERVICE_ONE_ID,
        count_as_live=expected_persisted_value,
    )


def test_should_not_allow_duplicate_service_names(
    client_request,
    mock_update_service_raise_httperror_duplicate_name,
    service_one,
):
    page = client_request.post(
        "main.service_name_change",
        service_id=SERVICE_ONE_ID,
        _data={"name": "SErvICE TWO"},
        _expected_status=200,
    )

    assert "This service name is already in use" in page.text


def test_service_name_change_doesnt_suppress_api_errors(client_request, mocker, service_one):
    mocker.patch(
        "app.main.views_nl.service_settings.index.service_api_client.update_service",
        side_effect=HTTPError(response=Mock(status_code=500)),
    )
    client_request.post(
        "main.service_name_change",
        service_id=SERVICE_ONE_ID,
        _data={"name": "SERVICE TWO"},
        _expected_status=500,
    )


def test_should_redirect_after_service_name_change(
    client_request,
    mock_update_service,
):
    client_request.post(
        "main.service_name_change",
        service_id=SERVICE_ONE_ID,
        _data={"name": "New Name"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_settings",
            service_id=SERVICE_ONE_ID,
        ),
    )

    mock_update_service.assert_called_once_with(SERVICE_ONE_ID, name="New Name", confirmed_unique=False)


class TestServiceDataRetention:
    @pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
    @pytest.mark.parametrize(
        "notification_volumes, show_guidance",
        (
            ({"email": 1_000_000, "sms": 0, "letter": 0}, True),
            ({"email": 0, "sms": 1_000_000, "letter": 0}, True),
            ({"email": 0, "sms": 0, "letter": 1_000_000}, True),
            ({"email": 0, "sms": 500_000, "letter": 500_000}, True),
            ({"email": 350_000, "sms": 350_000, "letter": 350_000}, True),
            ({"email": 999_999, "sms": 0, "letter": 0}, False),
        ),
    )
    def test_shown_guidance_if_declared_over_1mil_notifications_per_year(
        self, client_request, platform_admin_user, mocker, service_one, notification_volumes, show_guidance
    ):
        service_one["restricted"] = False
        for channel, volume in notification_volumes.items():
            mocker.patch(
                f"app.models.service.Service.volume_{channel}",
                create=True,
                new_callable=PropertyMock,
                return_value=volume,
            )
        mocker.patch("app.service_api_client.get_service_data_retention", return_value=[])
        mocker.patch("app.billing_api_client.get_annual_usage_for_service", return_value=[])

        client_request.login(platform_admin_user)
        page = client_request.get("main.service_data_retention", service_id=SERVICE_ONE_ID)
        assert (
            (
                "You cannot change the data retention period yourself. "
                "This is because your service is likely to send over 1 million messages this year."
            )
            in page.text
        ) is show_guidance

    @pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
    def test_post_from_service_that_declared_over_1mil_notifications_per_year_does_not_change_retention(
        self, client_request, platform_admin_user, mocker, service_one
    ):
        service_one["restricted"] = False
        for channel, volume in {"email": 1_000_000, "sms": 0, "letter": 0}.items():
            mocker.patch(
                f"app.models.service.Service.volume_{channel}",
                create=True,
                new_callable=PropertyMock,
                return_value=volume,
            )
        mocker.patch("app.service_api_client.get_service_data_retention", return_value=[])
        mocker.patch("app.billing_api_client.get_annual_usage_for_service", return_value=[])
        mock_set = mocker.patch("app.service_api_client.set_service_data_retention")

        client_request.login(platform_admin_user)
        page = client_request.post(
            "main.service_data_retention",
            service_id=SERVICE_ONE_ID,
            _data={"days_of_retention": 10},
            _expected_status=200,
        )
        assert mock_set.call_args_list == []
        assert (
            "You cannot change the data retention period yourself. "
            "This is because your service is likely to send over 1 million messages this year."
        ) in page.text

    @pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
    @pytest.mark.parametrize(
        "notification_volumes, show_guidance",
        (
            ({"email": 1_000_000, "sms": 0, "letter": 0}, True),
            ({"email": 0, "sms": 1_000_000, "letter": 0}, True),
            ({"email": 0, "sms": 0, "letter": 1_000_000}, True),
            ({"email": 0, "sms": 500_000, "letter": 500_000}, True),
            ({"email": 350_000, "sms": 350_000, "letter": 350_000}, True),
            ({"email": 999_999, "sms": 0, "letter": 0}, False),
        ),
    )
    def test_shown_guidance_if_sent_over_1mil_notifications_last_year(
        self, client_request, platform_admin_user, mocker, service_one, notification_volumes, show_guidance
    ):
        service_one["restricted"] = False
        for channel, volume in {"email": 0, "sms": 0, "letter": 0}.items():
            mocker.patch(
                f"app.models.service.Service.volume_{channel}",
                create=True,
                new_callable=PropertyMock,
                return_value=volume,
            )
        mocker.patch("app.service_api_client.get_service_data_retention", return_value=[])
        mocker.patch(
            "app.billing_api_client.get_annual_usage_for_service",
            side_effect=[
                [
                    {
                        "notification_type": channel,
                        "chargeable_units": volume,
                        "notifications_sent": volume,
                        "charged_units": 0,
                        "rate": 0.0165,
                        "cost": 0,
                    }
                    for channel, volume in notification_volumes.items()
                ],
                [],
            ],
        )

        client_request.login(platform_admin_user)
        page = client_request.get("main.service_data_retention", service_id=SERVICE_ONE_ID)
        assert (
            (
                "You cannot change the data retention period yourself. "
                "This is because your service is likely to send over 1 million messages this year."
            )
            in page.text
        ) is show_guidance

    @pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
    def test_post_from_service_that_sent_over_1mil_notifications_last_year_does_not_change_retention(
        self, client_request, platform_admin_user, mocker, service_one
    ):
        service_one["restricted"] = False
        for channel, volume in {"email": 0, "sms": 0, "letter": 0}.items():
            mocker.patch(
                f"app.models.service.Service.volume_{channel}",
                create=True,
                new_callable=PropertyMock,
                return_value=volume,
            )
        mocker.patch("app.service_api_client.get_service_data_retention", return_value=[])
        mocker.patch(
            "app.billing_api_client.get_annual_usage_for_service",
            side_effect=[
                [
                    {
                        "notification_type": "email",
                        "chargeable_units": 1000000,
                        "notifications_sent": 1000000,
                        "charged_units": 0,
                        "rate": 0.0165,
                        "cost": 0,
                    },
                ],
                [],
            ],
        )
        mocker.patch("app.utils.services.percentage_through_current_financial_year", return_value=25)
        mock_set = mocker.patch("app.service_api_client.set_service_data_retention")

        client_request.login(platform_admin_user)
        page = client_request.post(
            "main.service_data_retention",
            service_id=SERVICE_ONE_ID,
            _data={"days_of_retention": 10},
            _expected_status=200,
        )
        assert mock_set.call_args_list == []
        assert (
            "You cannot change the data retention period yourself. "
            "This is because your service is likely to send over 1 million messages this year."
        ) in page.text

    @pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
    @pytest.mark.parametrize(
        "notification_volumes, show_guidance",
        (
            ({"email": 500_000, "sms": 0, "letter": 0}, True),
            ({"email": 0, "sms": 500_000, "letter": 0}, True),
            ({"email": 0, "sms": 0, "letter": 500_000}, True),
            ({"email": 0, "sms": 250_000, "letter": 250_000}, True),
            ({"email": 166_000, "sms": 166_000, "letter": 166_000}, True),
            ({"email": 250_000, "sms": 0, "letter": 0}, True),
            ({"email": 249_999, "sms": 0, "letter": 0}, False),
        ),
    )
    def test_shown_guidance_if_predicted_to_send_over_1mil_notifications_this_year(
        self, client_request, platform_admin_user, mocker, service_one, notification_volumes, show_guidance
    ):
        service_one["restricted"] = False
        for channel, volume in {"email": 0, "sms": 0, "letter": 0}.items():
            mocker.patch(
                f"app.models.service.Service.volume_{channel}",
                create=True,
                new_callable=PropertyMock,
                return_value=volume,
            )
        mocker.patch("app.service_api_client.get_service_data_retention", return_value=[])
        mocker.patch(
            "app.billing_api_client.get_annual_usage_for_service",
            side_effect=[
                [],
                [
                    {
                        "notification_type": channel,
                        "chargeable_units": volume,
                        "notifications_sent": volume,
                        "charged_units": 0,
                        "rate": 0.0165,
                        "cost": 0,
                    }
                    for channel, volume in notification_volumes.items()
                ],
            ],
        )
        mocker.patch("app.utils.services.percentage_through_current_financial_year", return_value=25)

        client_request.login(platform_admin_user)
        page = client_request.get("main.service_data_retention", service_id=SERVICE_ONE_ID)
        assert (
            (
                "You cannot change the data retention period yourself. "
                "This is because your service is likely to send over 1 million messages this year."
            )
            in page.text
        ) is show_guidance

    @pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
    def test_post_from_service_sending_over_1mil_notifications_does_not_change_retention(
        self, client_request, platform_admin_user, mocker, service_one
    ):
        service_one["restricted"] = False
        for channel, volume in {"email": 0, "sms": 0, "letter": 0}.items():
            mocker.patch(
                f"app.models.service.Service.volume_{channel}",
                create=True,
                new_callable=PropertyMock,
                return_value=volume,
            )
        mocker.patch("app.service_api_client.get_service_data_retention", return_value=[])
        mocker.patch(
            "app.billing_api_client.get_annual_usage_for_service",
            side_effect=[
                [],
                [
                    {
                        "notification_type": "email",
                        "chargeable_units": 1000000,
                        "notifications_sent": 1000000,
                        "charged_units": 0,
                        "rate": 0.0165,
                        "cost": 0,
                    },
                ],
            ],
        )
        mocker.patch("app.utils.services.percentage_through_current_financial_year", return_value=25)
        mock_set = mocker.patch("app.service_api_client.set_service_data_retention")

        client_request.login(platform_admin_user)
        page = client_request.post(
            "main.service_data_retention",
            service_id=SERVICE_ONE_ID,
            _data={"days_of_retention": 10},
            _expected_status=200,
        )
        assert mock_set.call_args_list == []
        assert (
            "You cannot change the data retention period yourself. "
            "This is because your service is likely to send over 1 million messages this year."
        ) in page.text

    @pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
    def test_shown_guidance_if_service_is_in_trial_mode(self, client_request, platform_admin_user, mocker, service_one):
        service_one["restricted"] = True
        for channel, volume in {"email": 0, "sms": 0, "letter": 0}.items():
            mocker.patch(
                f"app.models.service.Service.volume_{channel}",
                create=True,
                new_callable=PropertyMock,
                return_value=volume,
            )
        mocker.patch("app.service_api_client.get_service_data_retention", return_value=[])
        mocker.patch("app.billing_api_client.get_annual_usage_for_service", return_value=[])
        mocker.patch("app.utils.services.percentage_through_current_financial_year", return_value=25)

        client_request.login(platform_admin_user)
        page = client_request.get("main.service_data_retention", service_id=SERVICE_ONE_ID)
        assert (
            normalize_spaces("You cannot change your data retention period while your service is in trial mode.")
            in page.text
        )

    @pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
    def test_post_from_trial_mode_service_does_not_change_retention(
        self, client_request, platform_admin_user, mocker, service_one
    ):
        service_one["restricted"] = True
        for channel, volume in {"email": 0, "sms": 0, "letter": 0}.items():
            mocker.patch(
                f"app.models.service.Service.volume_{channel}",
                create=True,
                new_callable=PropertyMock,
                return_value=volume,
            )
        mocker.patch("app.service_api_client.get_service_data_retention", return_value=[])
        mocker.patch("app.billing_api_client.get_annual_usage_for_service", return_value=[])
        mocker.patch("app.utils.services.percentage_through_current_financial_year", return_value=25)
        mock_set = mocker.patch("app.service_api_client.set_service_data_retention")

        client_request.login(platform_admin_user)
        page = client_request.post(
            "main.service_data_retention",
            service_id=SERVICE_ONE_ID,
            _data={"days_of_retention": 10},
            _expected_status=200,
        )
        assert mock_set.call_args_list == []
        assert (
            normalize_spaces("You cannot change your data retention period while your service is in trial mode.")
            in page.text
        )

    @pytest.mark.parametrize(
        "service_retentions, expected_retention",
        (
            ({}, "7"),
            ({"email": 3}, None),
            ({"sms": 3}, None),
            ({"letter": 3}, None),
            ({"email": 3, "sms": 3, "letter": 3}, "3"),
            ({"email": 3, "sms": 5, "letter": 7}, None),
        ),
    )
    def test_input_prefilled_if_all_existing_retention_periods_are_the_same(
        self, client_request, platform_admin_user, mocker, service_one, service_retentions, expected_retention
    ):
        service_one["restricted"] = False
        for channel, volume in {"email": 0, "sms": 0, "letter": 0}.items():
            mocker.patch(
                f"app.models.service.Service.volume_{channel}",
                create=True,
                new_callable=PropertyMock,
                return_value=volume,
            )
        mocker.patch(
            "app.service_api_client.get_service_data_retention",
            return_value=[
                {
                    "id": str(sample_uuid()),
                    "service_id": str(sample_uuid()),
                    "service_name": "service name",
                    "notification_type": channel,
                    "days_of_retention": retention,
                    "created_at": datetime.now(),
                    "updated_at": None,
                }
                for channel, retention in service_retentions.items()
            ],
        )
        mocker.patch("app.billing_api_client.get_annual_usage_for_service", return_value=[])
        mocker.patch("app.utils.services.percentage_through_current_financial_year", return_value=25)

        client_request.login(platform_admin_user)
        page = client_request.get("main.service_data_retention", service_id=SERVICE_ONE_ID)
        assert page.select_one("input[name=days_of_retention]").get("value") == expected_retention

    @pytest.mark.parametrize(
        "value, expected_error",
        (
            ("", "Error: Enter a number of days"),
            ("a", "Error: Enter the number of days in digits"),
            ("1", "Error: The number of days must be between 3 and 90"),
        ),
    )
    def test_post_input_validation(
        self, client_request, platform_admin_user, mocker, value, expected_error, service_one
    ):
        service_one["restricted"] = False
        for channel, volume in {"email": 0, "sms": 0, "letter": 0}.items():
            mocker.patch(
                f"app.models.service.Service.volume_{channel}",
                create=True,
                new_callable=PropertyMock,
                return_value=volume,
            )
        mocker.patch(
            "app.service_api_client.get_service_data_retention",
            return_value=[],
        )
        mocker.patch("app.billing_api_client.get_annual_usage_for_service", return_value=[])
        mocker.patch("app.utils.services.percentage_through_current_financial_year", return_value=25)

        client_request.login(platform_admin_user)
        page = client_request.post(
            "main.service_data_retention",
            service_id=SERVICE_ONE_ID,
            _data={"days_of_retention": value},
            _expected_status=200,
        )
        assert expected_error in page.text

    @pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
    def test_post_updates_volumes_for_all_channels(self, client_request, platform_admin_user, mocker, service_one):
        service_one["restricted"] = False
        for channel, volume in {"email": 0, "sms": 0, "letter": 0}.items():
            mocker.patch(
                f"app.models.service.Service.volume_{channel}",
                create=True,
                new_callable=PropertyMock,
                return_value=volume,
            )
        mocker.patch(
            "app.service_api_client.get_service_data_retention",
            return_value=[],
        )
        mocker.patch("app.billing_api_client.get_annual_usage_for_service", return_value=[])
        mocker.patch("app.utils.services.percentage_through_current_financial_year", return_value=25)
        mock_set = mocker.patch("app.service_api_client.set_service_data_retention")
        mock_flash = mocker.patch("app.main.views_nl.service_settings.index.flash")

        client_request.login(platform_admin_user)
        client_request.post(
            "main.service_data_retention",
            service_id=SERVICE_ONE_ID,
            _data={"days_of_retention": "3"},
        )
        assert mock_set.call_args_list == [mocker.call(service_id=SERVICE_ONE_ID, days_of_retention=3)]
        assert mock_flash.call_args_list == [
            mocker.call("You’ve changed the data retention period to 3 days", "default")
        ]


@pytest.mark.parametrize(
    "volumes, displayed_volumes",
    (
        (
            (("email", None), ("sms", None), ("letter", None)),
            (None, None, None),
        ),
        (
            (("email", 1234), ("sms", 0), ("letter", 999)),
            ("1,234", "0", "999"),
        ),
    ),
)
@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_estimate_volumes(
    client_request,
    volumes,
    displayed_volumes,
    mocker,
):
    for channel, volume in volumes:
        mocker.patch(
            f"app.models.service.Service.volume_{channel}",
            create=True,
            new_callable=PropertyMock,
            return_value=volume,
        )
    page = client_request.get("main.estimate_usage", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Tell us how many messages you expect to send"
    for channel, label, hint, value in (
        (
            "email",
            "How many emails do you expect to send in the next year?",
            "For example, 50,000",
            displayed_volumes[0],
        ),
        (
            "sms",
            "How many text messages do you expect to send in the next year?",
            "For example, 50,000",
            displayed_volumes[1],
        ),
        (
            "letter",
            "How many letters do you expect to send in the next year?",
            "For example, 50,000",
            displayed_volumes[2],
        ),
    ):
        assert normalize_spaces(page.select_one(f"label[for=volume_{channel}]").text) == label
        assert normalize_spaces(page.select_one(f"#volume_{channel}-hint").text) == hint
        assert page.select_one(f"#volume_{channel}").get("value") == value


def test_should_show_persist_estimated_volumes(
    client_request,
    mock_update_service,
):
    client_request.post(
        "main.estimate_usage",
        service_id=SERVICE_ONE_ID,
        _data={
            "volume_email": "1,234,567",
            "volume_sms": "",
            "volume_letter": "098",
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.request_to_go_live",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        volume_email=1234567,
        volume_sms=0,
        volume_letter=98,
    )


def test_should_error_if_bad_estimations_given(
    client_request,
    mock_update_service,
):
    page = client_request.post(
        "main.estimate_usage",
        service_id=SERVICE_ONE_ID,
        _data={
            "volume_email": "1234",
            "volume_sms": "2000000001",
            "volume_letter": "9876",
        },
        _expected_status=200,
    )
    assert (
        normalize_spaces(page.select_one("#volume_sms-error").text)
        == "Error: The number of text messages must be 2,000,000,000 or less"
    )
    assert mock_update_service.called is False


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_error_if_all_volumes_zero(
    client_request,
    mock_update_service,
):
    page = client_request.post(
        "main.estimate_usage",
        service_id=SERVICE_ONE_ID,
        _data={
            "volume_email": "",
            "volume_sms": "0",
            "volume_letter": "0,00 0",
        },
        _expected_status=200,
    )
    assert page.select("input[type=text]")[0].get("value") is None
    assert page.select("input[type=text]")[1]["value"] == "0"
    assert page.select("input[type=text]")[2]["value"] == "0,00 0"
    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        "Enter the number of messages you expect to send in the next year"
    )
    assert mock_update_service.called is False


def test_should_not_default_to_zero_if_some_fields_dont_validate(
    client_request,
    mock_update_service,
):
    page = client_request.post(
        "main.estimate_usage",
        service_id=SERVICE_ONE_ID,
        _data={
            "volume_email": "1234",
            "volume_sms": "",
            "volume_letter": "aaaaaaaaaaaaa",
        },
        _expected_status=200,
    )
    assert page.select("input[type=text]")[0]["value"] == "1234"
    assert page.select("input[type=text]")[1].get("value") is None
    assert page.select("input[type=text]")[2]["value"] == "aaaaaaaaaaaaa"
    assert normalize_spaces(page.select_one("#volume_letter-error").text) == (
        "Error: Enter the number of letters in digits"
    )
    assert mock_update_service.called is False


@pytest.mark.parametrize(
    (
        "has_team_members_with_manage_service_permission,"
        "has_templates,"
        "has_email_templates,"
        "has_sms_templates,"
        "has_email_reply_to_address,"
        "shouldnt_use_govuk_as_sms_sender,"
        "sms_sender_is_govuk,"
        "volume_email,"
        "volume_sms,"
        "volume_letter,"
        "confirmed_unique,"
        "expected_readyness,"
        "agreement_signed,"
    ),
    (
        (  # Just sending email
            True,
            True,
            True,
            False,
            True,
            True,
            True,
            1,
            0,
            0,
            True,
            True,
            True,
        ),
        (  # Needs to set reply to address
            True,
            True,
            True,
            False,
            False,
            True,
            True,
            1,
            0,
            1,
            True,
            False,
            True,
        ),
        (  # Just sending SMS
            True,
            True,
            False,
            True,
            True,
            True,
            False,
            0,
            1,
            0,
            True,
            True,
            True,
        ),
        (  # Needs to change SMS sender
            True,
            True,
            False,
            True,
            True,
            True,
            True,
            0,
            1,
            0,
            True,
            False,
            True,
        ),
        (  # Needs team members
            False,
            True,
            False,
            True,
            True,
            True,
            False,
            1,
            0,
            0,
            True,
            False,
            True,
        ),
        (  # Needs templates
            True,
            False,
            False,
            True,
            True,
            True,
            False,
            0,
            1,
            0,
            True,
            False,
            True,
        ),
        (  # Just confirm unique service
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            1,
            0,
            0,
            False,
            False,
            True,
        ),
        (  # Not done anything yet
            False,
            False,
            False,
            False,
            False,
            False,
            True,
            None,
            None,
            None,
            False,
            False,
            False,
        ),
    ),
)
def test_ready_to_go_live(
    client_request,
    mocker,
    mock_get_service_organisation,
    has_team_members_with_manage_service_permission,
    has_templates,
    has_email_templates,
    has_sms_templates,
    has_email_reply_to_address,
    shouldnt_use_govuk_as_sms_sender,
    sms_sender_is_govuk,
    volume_email,
    volume_sms,
    volume_letter,
    confirmed_unique,
    expected_readyness,
    agreement_signed,
):
    mocker.patch(
        "app.organisations_client.get_organisation", return_value=organisation_json(agreement_signed=agreement_signed)
    )

    for prop in {
        "has_team_members_with_manage_service_permission",
        "has_templates",
        "has_email_templates",
        "has_sms_templates",
        "has_email_reply_to_address",
        "shouldnt_use_govuk_as_sms_sender",
        "sms_sender_is_govuk",
    }:
        mocker.patch(f"app.models.service.Service.{prop}", new_callable=PropertyMock).return_value = locals()[prop]

    for channel, volume in (
        ("sms", volume_sms),
        ("email", volume_email),
        ("letter", volume_letter),
    ):
        mocker.patch(
            f"app.models.service.Service.volume_{channel}",
            create=True,
            new_callable=PropertyMock,
            return_value=volume,
        )

    service = app.models.service.Service({"id": SERVICE_ONE_ID, "confirmed_unique": confirmed_unique})

    assert service.go_live_checklist_completed is expected_readyness


@pytest.mark.parametrize(
    "route",
    [
        "main.service_settings",
        "main.service_name_change",
        "main.archive_service",
    ],
)
def test_route_permissions(
    notify_admin,
    client_request,
    api_user_active,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_invites_for_service,
    single_sms_sender,
    route,
    mock_get_service_settings_page_common,
    mock_get_service_templates,
    mocker,
):
    validate_route_permission(
        mocker,
        notify_admin,
        "GET",
        200,
        url_for(route, service_id=service_one["id"]),
        ["manage_service"],
        api_user_active,
        service_one,
        session={"service_name_change": "New Service Name"},
    )


@pytest.mark.parametrize(
    "route",
    [
        "main.service_settings",
        "main.service_name_change",
        "main.service_switch_live",
        "main.archive_service",
    ],
)
def test_route_invalid_permissions(
    notify_admin,
    client_request,
    api_user_active,
    service_one,
    route,
    mock_get_service_templates,
    mock_get_invites_for_service,
    mocker,
):
    validate_route_permission(
        mocker,
        notify_admin,
        "GET",
        403,
        url_for(route, service_id=service_one["id"]),
        ["blah"],
        api_user_active,
        service_one,
    )


@pytest.mark.parametrize(
    "route",
    [
        "main.service_settings",
        "main.service_name_change",
    ],
)
def test_route_for_platform_admin(
    notify_admin,
    client_request,
    platform_admin_user,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    single_sms_sender,
    route,
    mock_get_service_settings_page_common,
    mock_get_service_templates,
    mock_get_invites_for_service,
    mocker,
):
    validate_route_permission(
        mocker,
        notify_admin,
        "GET",
        200,
        url_for(route, service_id=service_one["id"]),
        [],
        platform_admin_user,
        service_one,
        session={"service_name_change": "New Service Name"},
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_and_more_hint_appears_on_settings_with_more_than_just_a_single_sender(
    client_request,
    service_one,
    multiple_reply_to_email_addresses,
    multiple_letter_contact_blocks,
    multiple_sms_senders,
    mock_get_service_settings_page_common,
):
    service_one["permissions"] = ["email", "sms", "letter"]

    page = client_request.get("main.service_settings", service_id=service_one["id"])

    def get_row(page, label):
        return normalize_spaces(
            find_element_by_tag_and_partial_text(page, tag=".govuk-summary-list__row", string=label).text
        )

    assert (
        get_row(page, "Reply-to email addresses")
        == "Reply-to email addresses test@example.com …and 2 more Manage reply-to email addresses"
    )
    assert (
        get_row(page, "Text message sender IDs")
        == "Text message sender IDs 07812398712 …and 2 more Manage text message sender IDs"
    )
    assert get_row(page, "Sender addresses") == "Sender addresses 1 Example Street …and 2 more Manage sender addresses"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "sender_list_page, index, expected_output",
    [
        ("main.service_email_reply_to", 0, "test@example.com (default) Change test@example.com"),
        ("main.service_letter_contact_details", 1, "1 Example Street (default) Change 1 Example Street"),
        ("main.service_sms_senders", 0, "GOVUK (default) Change GOVUK"),
    ],
)
def test_api_ids_dont_show_on_option_pages_with_a_single_sender(
    client_request,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    single_sms_sender,
    sender_list_page,
    index,
    expected_output,
):
    rows = client_request.get(sender_list_page, service_id=SERVICE_ONE_ID).select(".user-list-item")

    assert normalize_spaces(rows[index].text) == expected_output
    assert len(rows) == index + 1


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "sender_list_page,endpoint_to_mock,sample_data,expected_items,",
    [
        (
            "main.service_email_reply_to",
            "app.service_api_client.get_reply_to_email_addresses",
            create_multiple_email_reply_to_addresses(),
            [
                "test@example.com (default) Change test@example.com ID: 1234",
                "test2@example.com Change test2@example.com ID: 5678",
                "test3@example.com Change test3@example.com ID: 9457",
            ],
        ),
        (
            "main.service_letter_contact_details",
            "app.service_api_client.get_letter_contacts",
            create_multiple_letter_contact_blocks(),
            [
                "Blank Make default",
                "1 Example Street (default) Change 1 Example Street ID: 1234",
                "2 Example Street Change 2 Example Street ID: 5678",
                "foo<bar>baz Change foo <bar> baz ID: 9457",
            ],
        ),
        (
            "main.service_sms_senders",
            "app.service_api_client.get_sms_senders",
            create_multiple_sms_senders(),
            [
                "Example (default and receives replies) Change Example ID: 1234",
                "Example 2 Change Example 2 ID: 5678",
                "Example 3 Change Example 3 ID: 9457",
            ],
        ),
    ],
)
def test_default_option_shows_for_default_sender(
    client_request,
    mocker,
    sender_list_page,
    endpoint_to_mock,
    sample_data,
    expected_items,
):
    mocker.patch(endpoint_to_mock, return_value=sample_data)

    rows = client_request.get(sender_list_page, service_id=SERVICE_ONE_ID).select(".user-list-item")

    assert [normalize_spaces(row.text) for row in rows] == expected_items


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_remove_default_from_default_letter_contact_block(
    client_request,
    multiple_letter_contact_blocks,
    mock_update_letter_contact,
):
    letter_contact_details_page = url_for(
        "main.service_letter_contact_details",
        service_id=SERVICE_ONE_ID,
    )

    link = client_request.get_url(letter_contact_details_page).select_one(".user-list-item a")
    assert link.text == "Make default"
    assert link["href"] == url_for(
        ".service_make_blank_default_letter_contact",
        service_id=SERVICE_ONE_ID,
    )

    client_request.get_url(
        link["href"],
        _expected_status=302,
        _expected_redirect=letter_contact_details_page,
    )

    mock_update_letter_contact.assert_called_once_with(
        SERVICE_ONE_ID,
        letter_contact_id="1234",
        contact_block="1 Example Street",
        is_default=False,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "sender_list_page, endpoint_to_mock, expected_output",
    [
        (
            "main.service_email_reply_to",
            "app.service_api_client.get_reply_to_email_addresses",
            "You have not added any reply-to email addresses yet",
        ),
        ("main.service_letter_contact_details", "app.service_api_client.get_letter_contacts", "Blank (default)"),
        (
            "main.service_sms_senders",
            "app.service_api_client.get_sms_senders",
            "You have not added any text message sender IDs yet",
        ),
    ],
)
def test_no_senders_message_shows(client_request, sender_list_page, endpoint_to_mock, expected_output, mocker):
    mocker.patch(endpoint_to_mock, return_value=[])

    rows = client_request.get(sender_list_page, service_id=SERVICE_ONE_ID).select(".user-list-item")

    assert normalize_spaces(rows[0].text) == expected_output
    assert len(rows) == 1


@pytest.mark.parametrize(
    "reply_to_input, expected_error",
    [
        ("", "Error: Enter an email address"),
        ("testtest", "Error: Enter an email address in the correct format, like name@example.gov.uk"),
    ],
)
def test_incorrect_reply_to_email_address_input(
    reply_to_input, expected_error, client_request, no_reply_to_email_addresses
):
    page = client_request.post(
        "main.service_add_email_reply_to",
        service_id=SERVICE_ONE_ID,
        _data={"email_address": reply_to_input},
        _expected_status=200,
    )

    assert expected_error in normalize_spaces(page.select_one(".govuk-error-message").text)


@pytest.mark.parametrize(
    "contact_block_input, expected_error",
    [
        ("", "Error: Enter a sender address"),
        (
            "1 \n 2 \n 3 \n 4 \n 5 \n 6 \n 7 \n 8 \n 9 \n 0 \n a",
            "Error: This address is 11 lines long - the most you can have is 10 lines",
        ),
    ],
)
def test_incorrect_letter_contact_block_input(
    contact_block_input, expected_error, client_request, no_letter_contact_blocks
):
    page = client_request.post(
        "main.service_add_letter_contact",
        service_id=SERVICE_ONE_ID,
        _data={"letter_contact_block": contact_block_input},
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one(".govuk-error-message").text) == expected_error


@pytest.mark.parametrize(
    "sms_sender_input, expected_error",
    [
        ("elevenchars", None),
        ("11 chars", None),
        ("", "Error: Enter a text message sender ID"),
        ("abcdefghijkhgkg", "Error: Text message sender ID cannot be longer than 11 characters"),
        (
            r" ¯\_(ツ)_/¯ ",
            "Error: Text message sender ID can only include letters, "
            "numbers, spaces, and the following characters: & . - _",
        ),
        ("blood.co.uk", None),
        ("00123", "Error: Text message sender ID cannot start with 00"),
    ],
)
def test_incorrect_sms_sender_input(
    sms_sender_input,
    expected_error,
    client_request,
    no_sms_senders,
    mock_add_sms_sender,
    mocker,
):
    mocker.patch(
        "app.protected_sender_id_api_client.get_check_sender_id",
        return_value=False,
    )
    page = client_request.post(
        "main.service_add_sms_sender",
        service_id=SERVICE_ONE_ID,
        _data={"sms_sender": sms_sender_input},
        _expected_status=(200 if expected_error else 302),
    )
    error_message = page.select_one(".govuk-error-message")
    count_of_api_calls = len(mock_add_sms_sender.call_args_list)

    if not expected_error:
        assert not error_message
        assert count_of_api_calls == 1
    else:
        assert expected_error in error_message.text
        assert count_of_api_calls == 0


def test_incorrect_sms_sender_input_with_multiple_errors_only_shows_the_first(
    client_request, no_sms_senders, mock_add_sms_sender, mocker
):
    # Setup protected sender id mock
    mocker.patch(
        "app.protected_sender_id_api_client.get_check_sender_id",
        return_value=False,
    )
    # There are two errors with the SMS sender - the length and characters used. Only one
    # should be displayed on the page.
    page = client_request.post(
        "main.service_add_sms_sender", service_id=SERVICE_ONE_ID, _data={"sms_sender": "{}"}, _expected_status=200
    )

    error_message = page.select_one(".govuk-error-message")
    count_of_api_calls = len(mock_add_sms_sender.call_args_list)

    assert normalize_spaces(error_message.text) == "Error: Text message sender ID must be at least 3 characters long"
    assert count_of_api_calls == 0


@pytest.mark.parametrize(
    "reply_to_addresses, data, api_default_args",
    [
        ([], {}, True),
        (create_multiple_email_reply_to_addresses(), {}, False),
        (create_multiple_email_reply_to_addresses(), {"is_default": "y"}, True),
    ],
)
def test_add_reply_to_email_address_sends_test_notification(
    client_request,
    reply_to_addresses,
    data,
    api_default_args,
    mocker,
):
    mocker.patch("app.service_api_client.get_reply_to_email_addresses", return_value=reply_to_addresses)
    data["email_address"] = "test@example.com"
    mock_verify = mocker.patch(
        "app.service_api_client.verify_reply_to_email_address", return_value={"data": {"id": "123"}}
    )
    client_request.post(
        "main.service_add_email_reply_to",
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_verify_reply_to_address",
            service_id=SERVICE_ONE_ID,
            notification_id="123",
        )
        + f"?is_default={api_default_args}",
    )
    mock_verify.assert_called_once_with(SERVICE_ONE_ID, "test@example.com")


def test_service_add_reply_to_email_address_without_verification_for_platform_admin(
    client_request,
    platform_admin_user,
    mocker,
):
    client_request.login(platform_admin_user)

    mock_update = mocker.patch("app.service_api_client.add_reply_to_email_address")
    mocker.patch(
        "app.service_api_client.get_reply_to_email_addresses",
        return_value=[create_reply_to_email_address(is_default=True)],
    )
    data = {"is_default": "y", "email_address": "test@example.gov.uk"}

    client_request.post(
        "main.service_add_email_reply_to",
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_email_reply_to",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_update.assert_called_once_with(SERVICE_ONE_ID, email_address="test@example.gov.uk", is_default=True)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize("is_default,replace", [(True, "&replace=123"), (False, "")])
@pytest.mark.parametrize(
    "status,expected_failure,expected_success",
    [
        ("delivered", False, True),
        ("sending", False, False),
        ("permanent-failure", True, False),
    ],
)
@freeze_time("2018-06-01 11:11:00.061258")
def test_service_verify_reply_to_address(
    client_request,
    fake_uuid,
    get_non_default_reply_to_email_address,
    status,
    expected_failure,
    expected_success,
    is_default,
    replace,
    mocker,
):
    notification = {
        "id": fake_uuid,
        "status": status,
        "to": "email@example.gov.uk",
        "service_id": SERVICE_ONE_ID,
        "template_id": TEMPLATE_ONE_ID,
        "notification_type": "email",
        "created_at": "2018-06-01T11:10:52.499230+00:00",
    }
    mocker.patch("app.notification_api_client.get_notification", return_value=notification)
    mock_add_reply_to_email_address = mocker.patch("app.service_api_client.add_reply_to_email_address")
    mock_update_reply_to_email_address = mocker.patch("app.service_api_client.update_reply_to_email_address")
    mocker.patch("app.service_api_client.get_reply_to_email_addresses", return_value=[])
    page = client_request.get(
        "main.service_verify_reply_to_address",
        service_id=SERVICE_ONE_ID,
        notification_id=notification["id"],
        _optional_args=f"?is_default={is_default}{replace}",
    )
    assert page.select_one("h1").text == "Reply-to email address check"
    back_link = page.select_one(".govuk-back-link")
    assert back_link.text.strip() == "Back"
    if replace:
        assert "/email-reply-to/123/edit" in back_link["href"]
    else:
        assert "/email-reply-to/add" in back_link["href"]

    assert (page.select_one("div.banner-dangerous") is not None) == expected_failure
    assert (
        page.select_one("main p.govuk-body:nth-of-type(1)").text.strip() == "The check is complete."
    ) == expected_success

    if status == "delivered":
        if replace:
            mock_update_reply_to_email_address.assert_called_once_with(
                SERVICE_ONE_ID, "123", email_address=notification["to"], is_default=is_default
            )
            assert mock_add_reply_to_email_address.called is False
        else:
            mock_add_reply_to_email_address.assert_called_once_with(
                SERVICE_ONE_ID, email_address=notification["to"], is_default=is_default
            )
            assert mock_update_reply_to_email_address.called is False
    else:
        assert mock_add_reply_to_email_address.called is False
    if status == "permanent-failure":
        assert page.select_one("input", type="email").attrs["value"] == notification["to"]


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@freeze_time("2018-06-01 11:11:00.061258")
def test_add_reply_to_email_address_fails_if_notification_not_delivered_in_45_sec(
    client_request,
    fake_uuid,
    mocker,
):
    notification = {
        "id": fake_uuid,
        "status": "sending",
        "to": "email@example.gov.uk",
        "service_id": SERVICE_ONE_ID,
        "template_id": TEMPLATE_ONE_ID,
        "notification_type": "email",
        "created_at": "2018-06-01T11:10:12.499230+00:00",
    }
    mocker.patch("app.service_api_client.get_reply_to_email_addresses", return_value=[])
    mocker.patch("app.notification_api_client.get_notification", return_value=notification)
    mock_add_reply_to_email_address = mocker.patch("app.service_api_client.add_reply_to_email_address")
    page = client_request.get(
        "main.service_verify_reply_to_address",
        service_id=SERVICE_ONE_ID,
        notification_id=notification["id"],
        _optional_args=f"?is_default={False}",
    )
    expected_banner = page.select_one("div.banner-dangerous")
    assert "There’s a problem with your reply-to address" in expected_banner.text.strip()
    assert mock_add_reply_to_email_address.called is False


@pytest.mark.parametrize(
    "letter_contact_blocks, data, api_default_args",
    [
        ([], {}, True),  # no existing letter contact blocks
        (create_multiple_letter_contact_blocks(), {}, False),
        (create_multiple_letter_contact_blocks(), {"is_default": "y"}, True),
    ],
)
def test_add_letter_contact(
    letter_contact_blocks,
    data,
    api_default_args,
    client_request,
    mock_add_letter_contact,
    mocker,
):
    mocker.patch("app.service_api_client.get_letter_contacts", return_value=letter_contact_blocks)

    data["letter_contact_block"] = "1 Example Street"
    client_request.post("main.service_add_letter_contact", service_id=SERVICE_ONE_ID, _data=data)

    mock_add_letter_contact.assert_called_once_with(
        SERVICE_ONE_ID, contact_block="1 Example Street", is_default=api_default_args
    )


def test_add_letter_contact_when_coming_from_template(
    no_letter_contact_blocks,
    client_request,
    mock_add_letter_contact,
    fake_uuid,
    mock_get_service_letter_template,
    mock_update_service_template_sender,
):
    page = client_request.get(
        "main.service_add_letter_contact",
        service_id=SERVICE_ONE_ID,
        from_template=fake_uuid,
    )

    assert page.select_one(".govuk-back-link")["href"] == url_for(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    client_request.post(
        "main.service_add_letter_contact",
        service_id=SERVICE_ONE_ID,
        _data={
            "letter_contact_block": "1 Example Street",
        },
        from_template=fake_uuid,
        _expected_redirect=url_for(
            "main.view_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )

    mock_add_letter_contact.assert_called_once_with(
        SERVICE_ONE_ID,
        contact_block="1 Example Street",
        is_default=True,
    )
    mock_update_service_template_sender.assert_called_once_with(
        SERVICE_ONE_ID,
        fake_uuid,
        "1234",
    )


@pytest.mark.parametrize(
    "sms_senders, data, api_default_args",
    [
        ([], {}, True),
        (create_multiple_sms_senders(), {}, False),
        (create_multiple_sms_senders(), {"is_default": "y"}, True),
    ],
)
def test_add_sms_sender(
    sms_senders,
    data,
    api_default_args,
    client_request,
    mock_add_sms_sender,
    mocker,
):
    mocker.patch(
        "app.protected_sender_id_api_client.get_check_sender_id",
        return_value=False,
    )
    mocker.patch("app.service_api_client.get_sms_senders", return_value=sms_senders)
    data["sms_sender"] = "Example"
    client_request.post("main.service_add_sms_sender", service_id=SERVICE_ONE_ID, _data=data)

    mock_add_sms_sender.assert_called_once_with(SERVICE_ONE_ID, sms_sender="Example", is_default=api_default_args)


@pytest.mark.parametrize(
    "reply_to_addresses, checkbox_present",
    [
        ([], False),
        (create_multiple_email_reply_to_addresses(), True),
    ],
)
def test_default_box_doesnt_show_on_first_email_sender(
    reply_to_addresses,
    checkbox_present,
    client_request,
    mocker,
):
    mocker.patch("app.service_api_client.get_reply_to_email_addresses", return_value=reply_to_addresses)

    page = client_request.get("main.service_add_email_reply_to", service_id=SERVICE_ONE_ID)

    assert bool(page.select_one("[name=is_default]")) == checkbox_present


@pytest.mark.parametrize(
    "contact_blocks, checkbox_present", [([], False), (create_multiple_letter_contact_blocks(), True)]
)
def test_default_box_doesnt_show_on_first_letter_sender(
    contact_blocks,
    checkbox_present,
    client_request,
    mocker,
):
    mocker.patch("app.service_api_client.get_letter_contacts", return_value=contact_blocks)

    page = client_request.get("main.service_add_letter_contact", service_id=SERVICE_ONE_ID)

    assert bool(page.select_one("[name=is_default]")) == checkbox_present


@pytest.mark.parametrize(
    "reply_to_address, data",
    [
        (create_reply_to_email_address(is_default=True), {"is_default": "y"}),
        (create_reply_to_email_address(is_default=True), {}),
        (create_reply_to_email_address(is_default=False), {}),
        (create_reply_to_email_address(is_default=False), {"is_default": "y"}),
    ],
)
def test_edit_reply_to_email_address_sends_verification_notification_if_address_is_changed(
    reply_to_address,
    data,
    fake_uuid,
    client_request,
    mocker,
):
    mock_verify = mocker.patch(
        "app.service_api_client.verify_reply_to_email_address", return_value={"data": {"id": "123"}}
    )
    mocker.patch("app.service_api_client.get_reply_to_email_address", return_value=reply_to_address)
    data["email_address"] = "test@example.gov.uk"
    client_request.post(
        "main.service_edit_email_reply_to", service_id=SERVICE_ONE_ID, reply_to_email_id=fake_uuid, _data=data
    )
    mock_verify.assert_called_once_with(SERVICE_ONE_ID, "test@example.gov.uk")


def test_service_edit_email_reply_to_updates_email_address_without_verification_for_platform_admin(
    fake_uuid,
    client_request,
    platform_admin_user,
    mocker,
):
    client_request.login(platform_admin_user)

    mock_update = mocker.patch("app.service_api_client.update_reply_to_email_address")
    mocker.patch(
        "app.service_api_client.get_reply_to_email_address", return_value=create_reply_to_email_address(is_default=True)
    )
    data = {"is_default": "y", "email_address": "test@example.gov.uk"}

    client_request.post(
        "main.service_edit_email_reply_to",
        service_id=SERVICE_ONE_ID,
        reply_to_email_id=fake_uuid,
        _data=data,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_email_reply_to",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_update.assert_called_once_with(
        SERVICE_ONE_ID, reply_to_email_id=fake_uuid, email_address="test@example.gov.uk", is_default=True
    )


@pytest.mark.parametrize(
    "reply_to_address, data, api_default_args",
    [
        (create_reply_to_email_address(), {"is_default": "y"}, True),
        (create_reply_to_email_address(), {}, True),
        (create_reply_to_email_address(is_default=False), {}, False),
        (create_reply_to_email_address(is_default=False), {"is_default": "y"}, True),
    ],
)
def test_edit_reply_to_email_address_goes_straight_to_update_if_address_not_changed(
    reply_to_address,
    data,
    api_default_args,
    fake_uuid,
    client_request,
    mock_update_reply_to_email_address,
    mocker,
):
    mocker.patch("app.service_api_client.get_reply_to_email_address", return_value=reply_to_address)
    mock_verify = mocker.patch("app.service_api_client.verify_reply_to_email_address")
    data["email_address"] = "test@example.com"
    client_request.post(
        "main.service_edit_email_reply_to", service_id=SERVICE_ONE_ID, reply_to_email_id=fake_uuid, _data=data
    )

    mock_update_reply_to_email_address.assert_called_once_with(
        SERVICE_ONE_ID, reply_to_email_id=fake_uuid, email_address="test@example.com", is_default=api_default_args
    )
    assert mock_verify.called is False


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "url, header_text",
    [
        ("main.service_edit_email_reply_to", "Change reply-to email address"),
        ("main.service_add_email_reply_to", "Add reply-to email address"),
    ],
)
def test_add_and_edit_reply_to_email_address(
    fake_uuid,
    client_request,
    mock_update_reply_to_email_address,
    url,
    header_text,
    mocker,
):
    reply_to_email_address = create_reply_to_email_address()
    mocker.patch("app.service_api_client.get_reply_to_email_addresses", return_value=[reply_to_email_address])
    mocker.patch("app.service_api_client.get_reply_to_email_address", return_value=reply_to_email_address)
    error_message = "‘reply_to@example.com’ is already a reply-to email address for this service."
    mocker.patch(
        "app.service_api_client.verify_reply_to_email_address",
        side_effect=[
            HTTPError(
                response=Mock(status_code=409, json={"result": "error", "message": error_message}),
                message=error_message,
            )
        ],
    )
    data = {"is_default": "y", "email_address": "reply_to@example.com"}
    page = client_request.post(
        url, service_id=SERVICE_ONE_ID, reply_to_email_id=fake_uuid, _data=data, _follow_redirects=True
    )

    assert page.select_one("h1").text == header_text
    assert error_message in page.select_one(".govuk-error-message").text
    assert mock_update_reply_to_email_address.called is False


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "reply_to_address, default_choice_and_delete_link_expected",
    [
        (
            create_reply_to_email_address(is_default=False),
            True,
        ),
        (
            create_reply_to_email_address(is_default=True),
            False,
        ),
    ],
)
def test_shows_delete_link_for_get_request_for_edit_email_reply_to_address(
    reply_to_address,
    default_choice_and_delete_link_expected,
    client_request,
    mocker,
):
    mocker.patch("app.service_api_client.get_reply_to_email_address", return_value=reply_to_address)

    page = client_request.get(
        "main.service_edit_email_reply_to",
        service_id=SERVICE_ONE_ID,
        reply_to_email_id=sample_uuid(),
    )

    assert page.select_one(".govuk-back-link").text.strip() == "Back"
    assert page.select_one(".govuk-back-link")["href"] == url_for(
        ".service_email_reply_to",
        service_id=SERVICE_ONE_ID,
    )

    if default_choice_and_delete_link_expected:
        link = page.select_one(".page-footer a")
        assert normalize_spaces(link.text) == "Delete"
        assert link["href"] == url_for(
            "main.service_confirm_delete_email_reply_to", service_id=SERVICE_ONE_ID, reply_to_email_id=sample_uuid()
        )
        assert not page.select_one("input#is_default").has_attr("checked")

    else:
        assert not page.select(".page-footer a")


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "reply_to_address, default_choice_and_delete_link_expected, default_checkbox_checked",
    [
        (create_reply_to_email_address(is_default=False), True, False),
        (create_reply_to_email_address(is_default=False), True, True),
        (
            create_reply_to_email_address(is_default=True),
            False,
            False,  # not expecting a checkbox to even be shown to be ticked
        ),
    ],
)
def test_shows_delete_link_for_error_on_post_request_for_edit_email_reply_to_address(
    reply_to_address,
    default_choice_and_delete_link_expected,
    default_checkbox_checked,
    client_request,
    mocker,
):
    mocker.patch("app.service_api_client.get_reply_to_email_address", return_value=reply_to_address)

    data = {"email_address": "Enter an email address"}
    if default_checkbox_checked:
        data["is_default"] = "y"

    page = client_request.post(
        "main.service_edit_email_reply_to",
        service_id=SERVICE_ONE_ID,
        reply_to_email_id=sample_uuid(),
        _data=data,
        _expected_status=200,
    )

    assert page.select_one(".govuk-back-link").text.strip() == "Back"
    assert page.select_one(".govuk-back-link")["href"] == url_for(
        ".service_email_reply_to",
        service_id=SERVICE_ONE_ID,
    )
    assert (
        page.select_one(".govuk-error-message").text.strip()
        == "Error: Enter an email address in the correct format, like name@example.gov.uk"
    )
    assert page.select_one("input#email_address").get("value") == "Enter an email address"

    if default_choice_and_delete_link_expected:
        link = page.select_one(".page-footer a")
        assert normalize_spaces(link.text) == "Delete"
        assert link["href"] == url_for(
            "main.service_confirm_delete_email_reply_to", service_id=SERVICE_ONE_ID, reply_to_email_id=sample_uuid()
        )
        assert page.select_one("input#is_default").has_attr("checked") == default_checkbox_checked
    else:
        assert not page.select(".page-footer a")


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_confirm_delete_reply_to_email_address(fake_uuid, client_request, get_non_default_reply_to_email_address):
    page = client_request.get(
        "main.service_confirm_delete_email_reply_to",
        service_id=SERVICE_ONE_ID,
        reply_to_email_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        "Are you sure you want to delete this reply-to email address? Yes, delete"
    )
    assert "action" not in page.select_one(".banner-dangerous form")
    assert page.select_one(".banner-dangerous form")["method"] == "post"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_delete_reply_to_email_address(
    client_request,
    service_one,
    fake_uuid,
    get_non_default_reply_to_email_address,
    mocker,
):
    mock_delete = mocker.patch("app.service_api_client.delete_reply_to_email_address")
    client_request.post(
        ".service_delete_email_reply_to",
        service_id=SERVICE_ONE_ID,
        reply_to_email_id=fake_uuid,
        _expected_redirect=url_for(
            "main.service_email_reply_to",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_delete.assert_called_once_with(service_id=SERVICE_ONE_ID, reply_to_email_id=fake_uuid)


@pytest.mark.parametrize(
    "letter_contact_block, data, api_default_args",
    [
        (create_letter_contact_block(), {"is_default": "y"}, True),
        (create_letter_contact_block(), {}, True),
        (create_letter_contact_block(is_default=False), {}, False),
        (create_letter_contact_block(is_default=False), {"is_default": "y"}, True),
    ],
)
def test_edit_letter_contact_block(
    letter_contact_block,
    data,
    api_default_args,
    fake_uuid,
    client_request,
    mock_update_letter_contact,
    mocker,
):
    mocker.patch("app.service_api_client.get_letter_contact", return_value=letter_contact_block)
    data["letter_contact_block"] = "1 Example Street"
    client_request.post(
        "main.service_edit_letter_contact", service_id=SERVICE_ONE_ID, letter_contact_id=fake_uuid, _data=data
    )

    mock_update_letter_contact.assert_called_once_with(
        SERVICE_ONE_ID, letter_contact_id=fake_uuid, contact_block="1 Example Street", is_default=api_default_args
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_confirm_delete_letter_contact_block(
    fake_uuid,
    client_request,
    get_default_letter_contact_block,
):
    page = client_request.get(
        "main.service_confirm_delete_letter_contact",
        service_id=SERVICE_ONE_ID,
        letter_contact_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        "Are you sure you want to delete this contact block? Yes, delete"
    )
    assert "action" not in page.select_one(".banner-dangerous form")
    assert page.select_one(".banner-dangerous form")["method"] == "post"


def test_delete_letter_contact_block(
    client_request,
    service_one,
    fake_uuid,
    get_default_letter_contact_block,
    mocker,
):
    mock_delete = mocker.patch("app.service_api_client.delete_letter_contact")
    client_request.post(
        ".service_delete_letter_contact",
        service_id=SERVICE_ONE_ID,
        letter_contact_id=fake_uuid,
        _expected_redirect=url_for(
            "main.service_letter_contact_details",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_delete.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        letter_contact_id=fake_uuid,
    )


@pytest.mark.parametrize(
    "sms_sender, data, api_default_args",
    [
        (create_sms_sender(), {"is_default": "y", "sms_sender": "test"}, True),
        (create_sms_sender(), {"sms_sender": "test"}, True),
        (create_sms_sender(is_default=False), {"sms_sender": "test"}, False),
        (create_sms_sender(is_default=False), {"is_default": "y", "sms_sender": "test"}, True),
    ],
)
def test_edit_sms_sender(
    sms_sender,
    data,
    api_default_args,
    fake_uuid,
    client_request,
    mock_update_sms_sender,
    mocker,
):
    mocker.patch(
        "app.protected_sender_id_api_client.get_check_sender_id",
        return_value=False,
    )
    mocker.patch("app.service_api_client.get_sms_sender", return_value=sms_sender)

    client_request.post("main.service_edit_sms_sender", service_id=SERVICE_ONE_ID, sms_sender_id=fake_uuid, _data=data)

    mock_update_sms_sender.assert_called_once_with(
        SERVICE_ONE_ID, sms_sender_id=fake_uuid, sms_sender="test", is_default=api_default_args
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "sender_page, endpoint_to_mock, sender_details, default_message, params, checkbox_present",
    [
        (
            "main.service_edit_email_reply_to",
            "app.service_api_client.get_reply_to_email_address",
            create_reply_to_email_address(is_default=True),
            "This is the default reply-to address for service one emails",
            "reply_to_email_id",
            False,
        ),
        (
            "main.service_edit_email_reply_to",
            "app.service_api_client.get_reply_to_email_address",
            create_reply_to_email_address(is_default=False),
            "This is the default reply-to address for service one emails",
            "reply_to_email_id",
            True,
        ),
        (
            "main.service_edit_letter_contact",
            "app.service_api_client.get_letter_contact",
            create_letter_contact_block(is_default=True),
            "This is currently your default address for service one.",
            "letter_contact_id",
            False,
        ),
        (
            "main.service_edit_letter_contact",
            "app.service_api_client.get_letter_contact",
            create_letter_contact_block(is_default=False),
            "THIS TEXT WONT BE TESTED",
            "letter_contact_id",
            True,
        ),
        (
            "main.service_edit_sms_sender",
            "app.service_api_client.get_sms_sender",
            create_sms_sender(is_default=True),
            "This is the default text message sender ID.",
            "sms_sender_id",
            False,
        ),
        (
            "main.service_edit_sms_sender",
            "app.service_api_client.get_sms_sender",
            create_sms_sender(is_default=False),
            "This is the default text message sender ID.",
            "sms_sender_id",
            True,
        ),
    ],
)
def test_default_box_shows_on_non_default_sender_details_while_editing(
    fake_uuid,
    sender_page,
    endpoint_to_mock,
    sender_details,
    client_request,
    default_message,
    checkbox_present,
    params,
    mocker,
):
    page_arguments = {"service_id": SERVICE_ONE_ID}
    page_arguments[params] = fake_uuid

    mocker.patch(endpoint_to_mock, return_value=sender_details)

    page = client_request.get(sender_page, **page_arguments)

    if checkbox_present:
        assert page.select_one("[name=is_default]")
    else:
        assert normalize_spaces(page.select_one("form p").text) == (default_message)


def test_sender_details_are_escaped(client_request, mocker, fake_uuid):
    letter_contact_block = create_letter_contact_block(contact_block="foo\n\n<br>\n\nbar")
    mocker.patch("app.service_api_client.get_letter_contacts", return_value=[letter_contact_block])

    page = client_request.get(
        "main.service_letter_contact_details",
        service_id=SERVICE_ONE_ID,
    )

    # get the second row (first is the default Blank sender)
    assert "foo<br>bar" in normalize_spaces(page.select(".user-list-item")[1].text)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "sms_sender, expected_link_text, partial_href",
    [
        (
            create_sms_sender(is_default=False),
            "Delete",
            partial(url_for, "main.service_confirm_delete_sms_sender", sms_sender_id=sample_uuid()),
        ),
        (
            create_sms_sender(is_default=True),
            None,
            None,
        ),
    ],
)
def test_shows_delete_link_for_sms_sender(
    sms_sender,
    expected_link_text,
    partial_href,
    client_request,
    mocker,
):
    mocker.patch("app.service_api_client.get_sms_sender", return_value=sms_sender)

    page = client_request.get(
        "main.service_edit_sms_sender",
        service_id=SERVICE_ONE_ID,
        sms_sender_id=sample_uuid(),
    )

    link = page.select_one(".page-footer a")
    back_link = page.select_one(".govuk-back-link")

    assert back_link.text.strip() == "Back"
    assert back_link["href"] == url_for(
        ".service_sms_senders",
        service_id=SERVICE_ONE_ID,
    )

    if expected_link_text:
        assert normalize_spaces(link.text) == expected_link_text
        assert link["href"] == partial_href(service_id=SERVICE_ONE_ID)
    else:
        assert not link


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_confirm_delete_sms_sender(
    fake_uuid,
    client_request,
    get_non_default_sms_sender,
):
    page = client_request.get(
        "main.service_confirm_delete_sms_sender",
        service_id=SERVICE_ONE_ID,
        sms_sender_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        "Are you sure you want to delete this text message sender ID? Yes, delete"
    )
    assert "action" not in page.select_one(".banner-dangerous form")
    assert page.select_one(".banner-dangerous form")["method"] == "post"


@pytest.mark.parametrize(
    "sms_sender, expected_link_text",
    [
        (create_sms_sender(is_default=False, inbound_number_id="1234"), None),
        (create_sms_sender(is_default=True), None),
        (create_sms_sender(is_default=False), "Delete"),
    ],
)
@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_inbound_sms_sender_is_not_deleteable(
    client_request, service_one, fake_uuid, sms_sender, expected_link_text, mocker
):
    mocker.patch("app.service_api_client.get_sms_sender", return_value=sms_sender)

    page = client_request.get(
        ".service_edit_sms_sender",
        service_id=SERVICE_ONE_ID,
        sms_sender_id=fake_uuid,
    )

    back_link = page.select_one(".govuk-back-link")
    footer_link = page.select_one(".page-footer a")
    assert normalize_spaces(back_link.text) == "Back"

    if expected_link_text:
        assert normalize_spaces(footer_link.text) == expected_link_text
    else:
        assert not footer_link


def test_delete_sms_sender(
    client_request,
    service_one,
    fake_uuid,
    get_non_default_sms_sender,
    mocker,
):
    mock_delete = mocker.patch("app.service_api_client.delete_sms_sender")
    client_request.post(
        ".service_delete_sms_sender",
        service_id=SERVICE_ONE_ID,
        sms_sender_id=fake_uuid,
        _expected_redirect=url_for(
            "main.service_sms_senders",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_delete.assert_called_once_with(service_id=SERVICE_ONE_ID, sms_sender_id=fake_uuid)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "sms_sender, hide_textbox",
    [
        (create_sms_sender(is_default=False, inbound_number_id="1234"), True),
        (create_sms_sender(is_default=True), False),
    ],
)
def test_inbound_sms_sender_is_not_editable(client_request, service_one, fake_uuid, sms_sender, hide_textbox, mocker):
    mocker.patch("app.service_api_client.get_sms_sender", return_value=sms_sender)

    page = client_request.get(
        ".service_edit_sms_sender",
        service_id=SERVICE_ONE_ID,
        sms_sender_id=fake_uuid,
    )

    assert bool(page.select_one("input[name=sms_sender]")) != hide_textbox
    if hide_textbox:
        assert (
            normalize_spaces(page.select_one('form[method="post"] p').text)
            == "GOVUK This phone number receives replies and cannot be changed"
        )


def test_service_set_letter_branding_platform_admin_only(
    client_request,
):
    client_request.get(
        "main.service_set_branding",
        service_id=SERVICE_ONE_ID,
        branding_type="letter",
        _expected_status=403,
    )


@pytest.mark.parametrize(
    "letter_branding, expected_selected, expected_items",
    [
        # expected order: currently selected, then default, then rest alphabetically
        (
            None,
            "__NONE__",
            (
                ("__NONE__", "None"),
                (str(UUID(int=2)), "Animal and Plant Health Agency"),
                (str(UUID(int=0)), "HM Government"),
                (str(UUID(int=1)), "Land Registry"),
            ),
        ),
        (
            str(UUID(int=1)),
            str(UUID(int=1)),
            (
                (str(UUID(int=1)), "Land Registry"),
                ("__NONE__", "None"),
                (str(UUID(int=2)), "Animal and Plant Health Agency"),
                (str(UUID(int=0)), "HM Government"),
            ),
        ),
        (
            str(UUID(int=2)),
            str(UUID(int=2)),
            (
                (str(UUID(int=2)), "Animal and Plant Health Agency"),
                ("__NONE__", "None"),
                (str(UUID(int=0)), "HM Government"),
                (str(UUID(int=1)), "Land Registry"),
            ),
        ),
    ],
)
def test_service_set_letter_branding_prepopulates(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_all_letter_branding,
    letter_branding,
    expected_selected,
    expected_items,
    mocker,
):
    service_one["letter_branding"] = letter_branding

    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.service_set_branding",
        service_id=SERVICE_ONE_ID,
        branding_type="letter",
    )

    assert len(page.select("input[checked]")) == 1
    assert page.select("input[checked]")[0]["value"] == expected_selected

    for element in {"label[for^=branding_style]", "input[type=radio]"}:
        assert len(page.select(element)) == len(expected_items)

    for index, expected_item in enumerate(expected_items):
        expected_value, expected_label = expected_item
        assert normalize_spaces(page.select("label[for^=branding_style]")[index].text) == expected_label
        assert page.select("input[type=radio]")[index]["value"] == expected_value


@pytest.mark.parametrize(
    "selected_letter_branding, expected_post_data",
    [
        (str(UUID(int=1)), str(UUID(int=1))),
        ("__NONE__", None),
    ],
)
def test_service_set_letter_branding_redirects_to_preview_page_when_form_submitted(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mock_get_all_letter_branding,
    selected_letter_branding,
    expected_post_data,
):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.service_set_branding",
        branding_type="letter",
        _data={"branding_style": selected_letter_branding},
        _expected_status=302,
        _expected_redirect=url_for(
            ".service_preview_branding",
            branding_type="letter",
            branding_style=expected_post_data,
            service_id=SERVICE_ONE_ID,
        ),
        service_id=SERVICE_ONE_ID,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_service_preview_letter_branding_shows_preview_letter(
    client_request,
    platform_admin_user,
):
    client_request.login(platform_admin_user)

    page = client_request.get(
        "main.service_preview_branding",
        branding_type="letter",
        branding_style="hm-government",
        service_id=SERVICE_ONE_ID,
    )

    assert page.select_one("main img")["src"] == url_for(
        "no_cookie.letter_branding_preview_image",
        branding_style="hm-government",
    )
    assert page.select_one("main img")["alt"] == "Preview of letter branding"


@pytest.mark.parametrize(
    "selected_letter_branding, expected_post_data",
    [
        (str(UUID(int=1)), str(UUID(int=1))),
        ("__NONE__", None),
    ],
)
def test_service_preview_letter_branding_saves(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mock_get_organisation_services,
    mock_update_service,
    mock_update_organisation,
    mock_get_all_letter_branding,
    selected_letter_branding,
    expected_post_data,
):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.service_preview_branding",
        branding_type="letter",
        _data={"branding_style": selected_letter_branding},
        _expected_status=302,
        _expected_redirect=url_for("main.service_settings", service_id=SERVICE_ONE_ID),
        service_id=SERVICE_ONE_ID,
    )

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        letter_branding=expected_post_data,
    )
    assert mock_update_organisation.called is False


@pytest.mark.parametrize(
    "current_branding, expected_values, expected_labels",
    [
        (
            None,
            [
                "__NONE__",
                "1",
                "2",
                "3",
                "4",
                "5",
            ],
            ["GOV.UK", "org 1", "org 2", "org 3", "org 4", "org 5"],
        ),
        (
            "5",
            [
                "5",
                "__NONE__",
                "1",
                "2",
                "3",
                "4",
            ],
            [
                "org 5",
                "GOV.UK",
                "org 1",
                "org 2",
                "org 3",
                "org 4",
            ],
        ),
    ],
)
def test_should_show_branding_styles(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_all_email_branding,
    current_branding,
    expected_values,
    expected_labels,
    mocker,
):
    service_one["email_branding"] = current_branding
    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            email_branding_id=current_branding,
        ),
    )

    client_request.login(platform_admin_user)
    page = client_request.get("main.service_set_branding", service_id=SERVICE_ONE_ID, branding_type="email")

    branding_style_choices = page.select("input[name=branding_style]")

    radio_labels = [
        page.select_one(f'label[for="{branding_style_choices[idx]["id"]}"]').get_text().strip()
        for idx, element in enumerate(branding_style_choices)
    ]

    assert len(branding_style_choices) == 6

    for index, expected_value in enumerate(expected_values):
        assert branding_style_choices[index]["value"] == expected_value

    # radios should be in alphabetical order, based on their labels
    assert radio_labels == expected_labels

    assert "checked" in branding_style_choices[0].attrs
    assert "checked" not in branding_style_choices[1].attrs
    assert "checked" not in branding_style_choices[2].attrs
    assert "checked" not in branding_style_choices[3].attrs
    assert "checked" not in branding_style_choices[4].attrs
    assert "checked" not in branding_style_choices[5].attrs

    app.models.branding.AllEmailBranding._get_items.assert_called_once_with()
    app.service_api_client.get_service.assert_called_once_with(service_one["id"])


def test_should_send_branding_and_organisations_to_preview(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_organisation,
    mock_get_all_email_branding,
    mock_update_service,
):
    extra_args = {"service_id": SERVICE_ONE_ID}
    client_request.login(platform_admin_user)
    client_request.post(
        "main.service_set_branding",
        branding_type="email",
        _data={"branding_type": "org", "branding_style": "1"},
        _expected_status=302,
        _expected_location=url_for(
            "main.service_preview_branding", branding_type="email", branding_style="1", **extra_args
        ),
        **extra_args,
    )

    mock_get_all_email_branding.assert_called_once_with()


@pytest.mark.parametrize(
    "endpoint, extra_args",
    (
        (
            "main.service_preview_branding",
            {"service_id": SERVICE_ONE_ID, "branding_type": "email"},
        ),
    ),
)
def test_should_preview_email_branding(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    endpoint,
    extra_args,
):
    client_request.login(platform_admin_user)
    page = client_request.get(endpoint, branding_style="1", **extra_args)

    iframe = page.select_one("iframe.branding-preview")
    iframeURLComponents = urlparse(iframe["src"])
    iframeQString = parse_qs(iframeURLComponents.query)

    assert page.select_one("input", attrs={"id": "branding_style"})["value"] == "1"
    assert iframeURLComponents.path == "/_email"
    assert iframeQString["branding_style"] == ["1"]


@pytest.mark.parametrize(
    "email_branding_id, service_should_be_updated, expected_redirect,expected_branding_id_in_call",
    (
        (
            "174",  # Not already in the pool
            False,
            partial(
                url_for,
                "main.service_set_branding_add_to_branding_pool_step",
                service_id=SERVICE_ONE_ID,
                branding_type="email",
                branding_id="174",
            ),
            "174",
        ),
        (
            "email-branding-1-id",  # Already in the pool
            True,
            partial(
                url_for,
                "main.service_settings",
                service_id=SERVICE_ONE_ID,
            ),
            "email-branding-1-id",
        ),
        (
            "__NONE__",  # update to no branding, showing as GOV.UK branding
            True,
            partial(
                url_for,
                "main.service_settings",
                service_id=SERVICE_ONE_ID,
            ),
            None,
        ),
    ),
)
def test_should_set_branding_for_service_with_organisation(
    client_request,
    platform_admin_user,
    service_one,
    organisation_one,
    mock_get_organisation,
    mock_get_organisation_services,
    mock_update_service,
    mock_update_organisation,
    single_reply_to_email_address,
    single_sms_sender,
    mock_get_free_sms_fragment_limit,
    mock_get_service_data_retention,
    mock_get_email_branding_pool,
    email_branding_id,
    service_should_be_updated,
    expected_redirect,
    expected_branding_id_in_call,
    mocker,
):
    service_one["organisation"] = organisation_one
    service_id = SERVICE_ONE_ID
    email_branding_name = "branding1"

    mocker.patch(
        "app.email_branding_client.get_email_branding", return_value={"email_branding": {"name": email_branding_name}}
    )

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    client_request.login(platform_admin_user)
    client_request.post(
        "main.service_preview_branding",
        branding_type="email",
        _data={"branding_style": email_branding_id},
        service_id=service_id,
        _expected_redirect=expected_redirect(),
    )

    if service_should_be_updated:
        mock_update_service.assert_called_once_with(
            SERVICE_ONE_ID,
            email_branding=expected_branding_id_in_call,
        )
    else:
        assert mock_update_service.called is False


def test_should_set_branding_for_service_with_no_organisation(
    client_request,
    platform_admin_user,
    service_one,
    mock_update_service,
    single_reply_to_email_address,
    single_sms_sender,
    mock_get_free_sms_fragment_limit,
    mock_get_service_data_retention,
):
    service_id = SERVICE_ONE_ID
    email_branding_id = "174"
    client_request.login(platform_admin_user)
    client_request.post(
        "main.service_preview_branding",
        branding_type="email",
        _data={"branding_style": email_branding_id},
        service_id=service_id,
        _expected_redirect=url_for(
            "main.service_settings",
            service_id=SERVICE_ONE_ID,
        ),
    )

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        email_branding=email_branding_id,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_get_service_set_email_branding_add_to_branding_pool_step(
    client_request,
    platform_admin_user,
    service_one,
    organisation_one,
    mocker,
):
    service_one["organisation"] = organisation_one
    client_request.login(platform_admin_user)
    email_branding_id = "234"
    email_branding_name = "branding1"
    mocker.patch(
        "app.email_branding_client.get_email_branding", return_value={"email_branding": {"name": email_branding_name}}
    )
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    page = client_request.get(
        "main.service_set_branding_add_to_branding_pool_step",
        _expected_status=200,
        service_id=SERVICE_ONE_ID,
        branding_type="email",
        branding_id=email_branding_id,
    )
    assert f"Apply ‘{email_branding_name}’ branding" in normalize_spaces(page.select_one("title").text)


def test_service_set_email_branding_add_to_branding_pool_step_is_platform_admin_only(
    client_request,
    service_one,
    organisation_one,
    mocker,
):
    service_one["organisation"] = organisation_one
    email_branding_id = "234"
    email_branding_name = "branding1"
    mocker.patch(
        "app.email_branding_client.get_email_branding", return_value={"email_branding": {"name": email_branding_name}}
    )
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)
    mocker.patch("app.main.forms.AdminSetBrandingAddToBrandingPoolStepForm", return_value=None)
    client_request.get(
        "main.service_set_branding_add_to_branding_pool_step",
        _expected_status=403,
        service_id=SERVICE_ONE_ID,
        branding_type="email",
        branding_id=email_branding_id,
    )


@pytest.mark.parametrize("add_to_pool", ["yes", "no"])
@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_service_set_email_branding_add_to_branding_pool_step_choices_yes_or_no(
    client_request,
    platform_admin_user,
    service_one,
    organisation_one,
    add_to_pool,
    single_reply_to_email_address,
    single_sms_sender,
    mock_get_free_sms_fragment_limit,
    mock_get_service_data_retention,
    mock_update_service,
    mocker,
):
    client_request.login(platform_admin_user)
    service_one["organisation"] = organisation_one
    email_branding_id = "234"
    email_branding_name = "branding_1"

    mocker.patch(
        "app.email_branding_client.get_email_branding", return_value={"email_branding": {"name": email_branding_name}}
    )
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)
    mock_add_to_branding_pool = mocker.patch(
        "app.organisations_client.add_brandings_to_email_branding_pool", return_value=None
    )

    page = client_request.post(
        "main.service_set_branding_add_to_branding_pool_step",
        _data={"add_to_pool": add_to_pool},
        service_id=SERVICE_ONE_ID,
        branding_type="email",
        branding_id=email_branding_id,
        _follow_redirects=True,
    )

    mock_update_service.assert_called_once_with(SERVICE_ONE_ID, email_branding=email_branding_id)

    if add_to_pool == "yes":
        mock_add_to_branding_pool.assert_called_with(organisation_one["id"], [email_branding_id])
        assert (
            normalize_spaces(page.select_one("div.banner-default-with-tick").text)
            == f"The email branding has been set to {email_branding_name} "
            f"and it has been added to {organisation_one['name']}'s email branding pool"
        )

    elif add_to_pool == "no":
        mock_add_to_branding_pool.assert_not_called()
        assert (
            normalize_spaces(page.select_one("div.banner-default-with-tick").text)
            == f"The email branding has been set to {email_branding_name}"
        )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_get_service_set_letter_branding_add_to_branding_pool_step(
    client_request,
    platform_admin_user,
    service_one,
    organisation_one,
    mocker,
):
    service_one["organisation"] = organisation_one
    client_request.login(platform_admin_user)
    letter_branding_id = "234"
    letter_branding_name = "branding1"
    mocker.patch(
        "app.letter_branding_client.get_letter_branding",
        return_value={"name": letter_branding_name},
    )
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    page = client_request.get(
        "main.service_set_branding_add_to_branding_pool_step",
        _expected_status=200,
        service_id=SERVICE_ONE_ID,
        branding_type="letter",
        branding_id=letter_branding_id,
    )
    assert f"Apply ‘{letter_branding_name}’ branding" in normalize_spaces(page.select_one("title").text)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_get_service_set_letter_branding_add_to_branding_pool_step_protects_against_xss(
    client_request,
    platform_admin_user,
    service_one,
    organisation_one,
    mocker,
):
    service_one["organisation"] = organisation_one
    service_one["name"] = "<script>evil</script>"
    client_request.login(platform_admin_user)
    mocker.patch("app.letter_branding_client.get_letter_branding", return_value={"name": "branding 1"})
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    page = client_request.get(
        "main.service_set_branding_add_to_branding_pool_step",
        _expected_status=200,
        service_id=SERVICE_ONE_ID,
        branding_type="letter",
        branding_id="234",
    )
    form = page.select_one("form")
    for hint in form.select(".govuk-hint"):
        assert not hint.select("script")
        assert "apply this branding to ‘<script>evil</script>’" in normalize_spaces(hint.text).lower()


def test_service_set_letter_branding_add_to_branding_pool_step_is_platform_admin_only(
    client_request,
    service_one,
    organisation_one,
    mocker,
):
    service_one["organisation"] = organisation_one
    letter_branding_id = "234"
    letter_branding_name = "branding1"
    mocker.patch(
        "app.letter_branding_client.get_letter_branding",
        return_value={"name": letter_branding_name},
    )
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)
    mocker.patch("app.main.forms.AdminSetBrandingAddToBrandingPoolStepForm", return_value=None)
    client_request.get(
        "main.service_set_branding_add_to_branding_pool_step",
        _expected_status=403,
        service_id=SERVICE_ONE_ID,
        branding_type="letter",
        branding_id=letter_branding_id,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize("add_to_pool", ["yes", "no"])
def test_service_set_letter_branding_add_to_branding_pool_step_choices_yes_or_no(
    client_request,
    platform_admin_user,
    service_one,
    organisation_one,
    add_to_pool,
    single_sms_sender,
    single_reply_to_email_address,
    mock_get_free_sms_fragment_limit,
    mock_get_service_data_retention,
    mock_update_service,
    mocker,
):
    client_request.login(platform_admin_user)
    service_one["organisation"] = organisation_one
    letter_branding_id = "234"
    letter_branding_name = "branding_1"

    mocker.patch(
        "app.letter_branding_client.get_letter_branding",
        return_value={"name": letter_branding_name},
    )
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)
    mock_add_to_branding_pool = mocker.patch(
        "app.organisations_client.add_brandings_to_letter_branding_pool", return_value=None
    )

    page = client_request.post(
        "main.service_set_branding_add_to_branding_pool_step",
        _data={"add_to_pool": add_to_pool},
        service_id=SERVICE_ONE_ID,
        branding_type="letter",
        branding_id=letter_branding_id,
        _follow_redirects=True,
    )

    mock_update_service.assert_called_once_with(SERVICE_ONE_ID, letter_branding=letter_branding_id)

    if add_to_pool == "yes":
        mock_add_to_branding_pool.assert_called_with(organisation_one["id"], [letter_branding_id])
        assert (
            normalize_spaces(page.select_one("div.banner-default-with-tick").text)
            == f"The letter branding has been set to {letter_branding_name} "
            f"and it has been added to {organisation_one['name']}'s letter branding pool"
        )

    elif add_to_pool == "no":
        mock_add_to_branding_pool.assert_not_called()
        assert (
            normalize_spaces(page.select_one("div.banner-default-with-tick").text)
            == f"The letter branding has been set to {letter_branding_name}"
        )


@pytest.mark.parametrize("method", ["get", "post"])
@pytest.mark.parametrize(
    "endpoint, extra_args",
    [
        ("main.set_free_sms_allowance", {}),
        ("main.set_per_day_message_limit", {"notification_type": "email"}),
        ("main.set_per_minute_rate_limit", {}),
    ],
)
def test_organisation_type_pages_are_platform_admin_only(
    client_request,
    method,
    endpoint,
    extra_args,
):
    getattr(client_request, method)(
        endpoint,
        service_id=SERVICE_ONE_ID,
        **extra_args,
        _expected_status=403,
        _test_page_title=False,
    )


def test_should_show_page_to_set_sms_allowance(client_request, platform_admin_user, mock_get_free_sms_fragment_limit):
    client_request.login(platform_admin_user)
    page = client_request.get("main.set_free_sms_allowance", service_id=SERVICE_ONE_ID)

    assert normalize_spaces(page.select_one("label").text) == "Numbers of text message fragments per year"
    mock_get_free_sms_fragment_limit.assert_called_once_with(SERVICE_ONE_ID)


@freeze_time("2017-04-01 11:09:00.061258")
@pytest.mark.parametrize(
    "given_allowance, expected_api_argument",
    [
        ("0", 0),
        ("1", 1),
        ("250000", 250000),
        pytest.param("foo", "foo", marks=pytest.mark.xfail),
    ],
)
def test_should_set_sms_allowance(
    client_request,
    platform_admin_user,
    given_allowance,
    expected_api_argument,
    mock_get_free_sms_fragment_limit,
    mock_create_or_update_free_sms_fragment_limit,
):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.set_free_sms_allowance",
        service_id=SERVICE_ONE_ID,
        _data={
            "free_sms_allowance": given_allowance,
        },
        _expected_redirect=url_for(
            "main.service_settings",
            service_id=SERVICE_ONE_ID,
        ),
    )

    mock_create_or_update_free_sms_fragment_limit.assert_called_with(SERVICE_ONE_ID, expected_api_argument)


@pytest.mark.parametrize(
    "notification_type, expected_label",
    (
        ("email", "Daily email limit"),
        ("sms", "Daily text message limit"),
        ("letter", "Daily letter limit"),
    ),
)
def test_should_show_page_to_set_per_day_message_limit(
    client_request,
    platform_admin_user,
    notification_type,
    expected_label,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.set_per_day_message_limit", service_id=SERVICE_ONE_ID, notification_type=notification_type
    )
    assert normalize_spaces(page.select_one("label").text) == expected_label
    assert normalize_spaces(page.select_one("input[type=text]")["value"]) == "1,000"


@pytest.mark.parametrize("notification_type", ["sms", "email", "letter"])
@pytest.mark.parametrize(
    "new_limit, expected_api_argument",
    [
        ("1", 1),
        ("250000", 250_000),
        pytest.param("foo", "foo", marks=pytest.mark.xfail),
    ],
)
def test_set_per_day_message_limit(
    client_request,
    platform_admin_user,
    new_limit,
    expected_api_argument,
    mock_update_service,
    mocker,
    notification_type,
):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.set_per_day_message_limit",
        service_id=SERVICE_ONE_ID,
        notification_type=notification_type,
        _data={
            "message_limit": new_limit,
        },
    )
    assert mock_update_service.call_args_list == [
        mocker.call(SERVICE_ONE_ID, **{f"{notification_type}_message_limit": expected_api_argument})
    ]


def test_should_show_page_to_set_per_minute_rate_limit(
    client_request,
    platform_admin_user,
):
    client_request.login(platform_admin_user)
    page = client_request.get("main.set_per_minute_rate_limit", service_id=SERVICE_ONE_ID)
    assert normalize_spaces(page.select_one("label").text) == (
        "Number of messages the service can send in a rolling 60 second window"
    )
    assert normalize_spaces(page.select_one("input[type=text]")["value"]) == "3,000"


@pytest.mark.parametrize(
    "new_limit, expected_api_argument",
    [
        ("1", 1),
        ("250000", 250_000),
        ("250,000 ", 250_000),
        (" 250 000", 250_000),
    ],
)
def test_should_set_per_minute_rate_limit(
    client_request,
    platform_admin_user,
    new_limit,
    expected_api_argument,
    mock_update_service,
    mocker,
):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.set_per_minute_rate_limit",
        service_id=SERVICE_ONE_ID,
        _data={
            "rate_limit": new_limit,
        },
    )
    assert mock_update_service.call_args_list == [
        mocker.call(
            SERVICE_ONE_ID,
            rate_limit=expected_api_argument,
        )
    ]


@pytest.mark.parametrize(
    "endpoint, extra_args, form_data, expected_error_message, patches",
    (
        (
            "main.set_per_minute_rate_limit",
            {},
            {"rate_limit": ""},
            "Error: Enter a number of messages",
            {},
        ),
        (
            "main.set_per_minute_rate_limit",
            {},
            {"rate_limit": "-1"},
            "Error: Number must be greater than or equal to 0",
            {},
        ),
        (
            "main.set_per_minute_rate_limit",
            {},
            {"rate_limit": "foo"},
            "Error: Enter the number of messages in digits",
            {},
        ),
        (
            "main.set_per_day_message_limit",
            {"notification_type": "sms"},
            {"message_limit": ""},
            "Error: Enter a number of text messages",
            {},
        ),
        (
            "main.set_per_day_message_limit",
            {"notification_type": "email"},
            {"message_limit": "-1"},
            "Error: Number must be greater than or equal to 0",
            {},
        ),
        (
            "main.set_per_day_message_limit",
            {"notification_type": "email"},
            {"message_limit": "foo"},
            "Error: Enter the number of emails in digits",
            {},
        ),
        (
            "main.set_per_day_message_limit",
            {"notification_type": "letter"},
            {"message_limit": "12.34"},
            "Error: Enter the number of letters in digits",
            {},
        ),
        (
            "main.set_free_sms_allowance",
            {},
            {"free_sms_allowance": "-1"},
            "Error: Number must be greater than or equal to 0",
            {"app.billing_api_client.get_free_sms_fragment_limit_for_year": 0},
        ),
    ),
)
def test_should_show_error_for_invalid_message_limits(
    client_request,
    platform_admin_user,
    endpoint,
    extra_args,
    form_data,
    expected_error_message,
    mocker,
    patches,
):
    for patch, patch_retval in patches.items():
        mocker.patch(patch, return_value=patch_retval)

    client_request.login(platform_admin_user)
    page = client_request.post(
        endpoint,
        service_id=SERVICE_ONE_ID,
        **extra_args,
        _data=form_data,
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == expected_error_message


def test_old_set_letters_page_redirects(
    client_request,
):
    client_request.get(
        "main.service_set_letters",
        service_id=SERVICE_ONE_ID,
        _expected_status=301,
        _expected_redirect=url_for(
            "main.service_set_channel",
            service_id=SERVICE_ONE_ID,
            channel="letter",
        ),
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_unknown_channel_404s(
    client_request,
):
    client_request.get(
        "main.service_set_channel",
        service_id=SERVICE_ONE_ID,
        channel="message-in-a-bottle",
        _expected_status=404,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    (
        "channel,"
        "expected_first_para,"
        "expected_legend,"
        "initial_permissions,"
        "expected_initial_value,"
        "posted_value,"
        "expected_updated_permissions"
    ),
    [
        (
            "letter",
            "It costs between 59 pence and £1.76 to send a letter using Notify.",
            "Send letters",
            ["email", "sms"],
            "False",
            "True",
            ["email", "sms", "letter"],
        ),
        (
            "letter",
            "It costs between 59 pence and £1.76 to send a letter using Notify.",
            "Send letters",
            ["email", "sms", "letter"],
            "True",
            "False",
            ["email", "sms"],
        ),
        (
            "sms",
            "You have a free allowance of 250,000 text messages each financial year.",
            "Send text messages",
            [],
            "False",
            "True",
            ["sms"],
        ),
        (
            "email",
            "It’s free to send emails through GOV.UK Notify.",
            "Send emails",
            [],
            "False",
            "True",
            ["email"],
        ),
        (
            "email",
            "It’s free to send emails through GOV.UK Notify.",
            "Send emails",
            ["email", "sms", "letter"],
            "True",
            "True",
            ["email", "sms", "letter"],
        ),
    ],
)
def test_switch_service_channels_on_and_off(
    client_request,
    service_one,
    mocker,
    mock_get_free_sms_fragment_limit,
    mock_get_letter_rates,
    mock_get_sms_rate,
    channel,
    expected_first_para,
    expected_legend,
    initial_permissions,
    expected_initial_value,
    posted_value,
    expected_updated_permissions,
):
    mocked_fn = mocker.patch("app.service_api_client.update_service", return_value=service_one)
    service_one["permissions"] = initial_permissions

    page = client_request.get(
        "main.service_set_channel",
        service_id=service_one["id"],
        channel=channel,
    )

    assert normalize_spaces(page.select_one("main p").text) == expected_first_para
    assert normalize_spaces(page.select_one("legend").text) == expected_legend

    assert page.select_one("input[checked]")["value"] == expected_initial_value
    assert len(page.select("input[checked]")) == 1

    client_request.post(
        "main.service_set_channel",
        service_id=service_one["id"],
        channel=channel,
        _data={"enabled": posted_value},
        _expected_redirect=url_for(
            "main.service_settings",
            service_id=service_one["id"],
        ),
    )
    assert set(mocked_fn.call_args[1]["permissions"]) == set(expected_updated_permissions)
    assert mocked_fn.call_args[0][0] == service_one["id"]


@pytest.mark.parametrize(
    "permission, permissions, expected_checked",
    [
        ("international_sms", ["international_sms"], "True"),
        ("international_letters", ["international_letters"], "True"),
        ("international_sms", [""], "False"),
        ("international_letters", [""], "False"),
    ],
)
def test_show_international_sms_and_letters_as_radio_button(
    client_request,
    service_one,
    permission,
    permissions,
    expected_checked,
):
    service_one["permissions"] = permissions

    checked_radios = client_request.get(
        f"main.service_set_{permission}",
        service_id=service_one["id"],
    ).select(".govuk-radios__item input[checked]")

    assert len(checked_radios) == 1
    assert checked_radios[0]["value"] == expected_checked


def test_set_international_sms_page_shows_services_international_sms_limit(
    client_request,
    service_one,
):
    service_one["permissions"] = ["international_sms"]
    service_one["international_sms_message_limit"] = 56

    page = client_request.get("main.service_set_international_sms", service_id=service_one["id"])

    assert "56" in page.select(".govuk-body")[2].text


@pytest.mark.parametrize(
    "permission",
    (
        "international_sms",
        "international_letters",
    ),
)
@pytest.mark.parametrize(
    "post_value, permission_expected_in_api_call",
    [
        ("True", True),
        ("False", False),
    ],
)
def test_switch_service_enable_international_sms_and_letters(
    client_request,
    service_one,
    mocker,
    permission,
    post_value,
    permission_expected_in_api_call,
):
    mocked_fn = mocker.patch("app.service_api_client.update_service", return_value=service_one)
    client_request.post(
        f"main.service_set_{permission}",
        service_id=service_one["id"],
        _data={"enabled": post_value},
        _expected_redirect=url_for("main.service_settings", service_id=service_one["id"]),
    )

    if permission_expected_in_api_call:
        assert permission in mocked_fn.call_args[1]["permissions"]
    else:
        assert permission not in mocked_fn.call_args[1]["permissions"]

    assert mocked_fn.call_args[0][0] == service_one["id"]


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_should_show_page_to_set_per_day_international_sms_message_limit(
    client_request,
    service_one,
    mocker,
):
    service_one["permissions"] = ["international_sms"]
    mock_get_notification_count = mocker.patch("app.service_api_client.get_notification_count", return_value=1)

    page = client_request.get(
        "main.set_per_day_international_sms_message_limit",
        service_id=SERVICE_ONE_ID,
    )
    assert normalize_spaces(page.select_one("label").text) == "Daily international text message limit"
    # form prefilled with current limit
    assert normalize_spaces(page.select_one("input[type=text]")["value"]) == "500"
    # today's remaining limit pulled and displayed
    assert mock_get_notification_count.called_once_with(
        service_id=SERVICE_ONE_ID, notification_type="international_sms"
    )
    assert (
        normalize_spaces(page.select(".ajax-block-container")[0].text)
        == "You have sent 1 international text message today (499 remaining)."
    )


@pytest.mark.parametrize(
    "new_limit, expected_api_argument",
    [
        ("1", 1),
        ("1200", 1200),
        pytest.param("foo", "foo", marks=pytest.mark.xfail),
    ],
)
def test_set_per_day_international_sms_message_limit(
    client_request,
    new_limit,
    expected_api_argument,
    mock_update_service,
    mocker,
):
    client_request.post(
        "main.set_per_day_international_sms_message_limit",
        service_id=SERVICE_ONE_ID,
        _data={
            "message_limit": new_limit,
        },
    )
    assert mock_update_service.call_args_list == [
        mocker.call(SERVICE_ONE_ID, international_sms_message_limit=expected_api_argument)
    ]


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "daily_limit_type, limit_noun", (("sms", "text message"), ("email", "email"), ("letter", "letter"))
)
def test_should_show_daily_message_limit_page(
    client_request,
    service_one,
    daily_limit_type,
    limit_noun,
    mocker,
):
    mock_get_notification_count = mocker.patch("app.service_api_client.get_notification_count", return_value=1)

    page = client_request.get(
        "main.set_daily_message_limit",
        service_id=SERVICE_ONE_ID,
        daily_limit_type=daily_limit_type,
    )

    assert normalize_spaces(page.select_one("h1").text) == f"Daily {limit_noun} limit"

    # full limit pulled in and displayed
    assert normalize_spaces(page.select(".govuk-body")[0].text) == (f"You can send up to 1,000 {limit_noun}s per day.")

    # today's remaining limit pulled and displayed
    assert mock_get_notification_count.called_once_with(service_id=SERVICE_ONE_ID, notification_type=daily_limit_type)
    assert (
        normalize_spaces(page.select(".ajax-block-container")[0].text)
        == f"You have sent 1 {limit_noun} today (999 remaining)."
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "user, is_trial_service",
    (
        [create_platform_admin_user(), True],
        [create_platform_admin_user(), False],
        [create_active_user_with_permissions(), True],
        pytest.param(create_active_user_with_permissions(), False, marks=pytest.mark.xfail),
        pytest.param(create_active_user_no_settings_permission(), True, marks=pytest.mark.xfail),
    ),
)
def test_archive_service_after_confirm(
    client_request,
    mocker,
    mock_get_organisations,
    mock_get_organisation_by_domain,
    mock_get_service_and_organisation_counts,
    mock_get_organisations_and_services_for_user,
    mock_get_users_by_service,
    mock_get_service_templates,
    service_one,
    user,
    is_trial_service,
):
    service_one["restricted"] = is_trial_service
    mock_api = mocker.patch("app.service_api_client.post")
    mock_event = mocker.patch("app.main.views_nl.service_settings.index.Events.archive_service")
    redis_delete_mock = mocker.patch("app.notify_client.service_api_client.redis_client.delete")
    mocker.patch("app.notify_client.service_api_client.redis_client.delete_by_pattern")

    client_request.login(user)
    page = client_request.post(
        "main.archive_service",
        service_id=SERVICE_ONE_ID,
        _follow_redirects=True,
    )

    mock_api.assert_called_once_with(f"/service/{SERVICE_ONE_ID}/archive", data=None)
    mock_event.assert_called_once_with(service_id=SERVICE_ONE_ID, archived_by_id=user["id"])

    assert normalize_spaces(page.select_one("h1").text) == "Your services"
    assert normalize_spaces(page.select_one(".banner-default-with-tick").text) == "‘service one’ was deleted"
    # The one user which is part of this service has the sample_uuid as it's user ID
    assert call(f"user-{sample_uuid()}") in redis_delete_mock.call_args_list


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "user, is_trial_service",
    (
        [create_platform_admin_user(), True],
        [create_platform_admin_user(), False],
        [create_active_user_with_permissions(), True],
        pytest.param(
            create_active_user_with_permissions(),
            False,
            marks=pytest.mark.xfail,
        ),
        pytest.param(
            create_active_user_no_settings_permission(),
            True,
            marks=pytest.mark.xfail,
        ),
    ),
)
@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_archive_service_prompts_user(
    client_request,
    mocker,
    single_reply_to_email_address,
    single_letter_contact_block,
    service_one,
    single_sms_sender,
    mock_get_service_settings_page_common,
    user,
    is_trial_service,
):
    mock_api = mocker.patch("app.service_api_client.post")
    service_one["restricted"] = is_trial_service
    client_request.login(user)

    settings_page = client_request.get("main.archive_service", service_id=SERVICE_ONE_ID)
    delete_link = settings_page.select(".page-footer-link a")[0]
    assert normalize_spaces(delete_link.text) == "Delete this service"
    assert delete_link["href"] == url_for(
        "main.archive_service",
        service_id=SERVICE_ONE_ID,
    )

    delete_page = client_request.get(
        "main.archive_service",
        service_id=SERVICE_ONE_ID,
    )
    assert "Are you sure you want to delete" in normalize_spaces(delete_page.select_one(".banner-dangerous").text)
    assert mock_api.called is False


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_cant_archive_inactive_service(
    client_request,
    platform_admin_user,
    service_one,
    single_reply_to_email_address,
    single_letter_contact_block,
    single_sms_sender,
    mock_get_service_settings_page_common,
):
    service_one["active"] = False

    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.service_settings",
        service_id=service_one["id"],
    )

    assert "Delete service" not in {a.text for a in page.select("a.button")}


@pytest.mark.parametrize(
    "contact_details_type, contact_details_value",
    [
        ("url", "http://example.com/"),
        ("email_address", "me@example.com"),
        ("phone_number", "0207 123 4567"),
    ],
)
def test_send_files_by_email_contact_details_prefills_the_form_with_the_existing_contact_details(
    client_request,
    service_one,
    contact_details_type,
    contact_details_value,
):
    service_one["contact_link"] = contact_details_value

    page = client_request.get("main.send_files_by_email_contact_details", service_id=SERVICE_ONE_ID)
    assert page.select_one(f"input[name=contact_details_type][value={contact_details_type}]").has_attr("checked")
    assert page.select_one(f"input#{contact_details_type}")["value"] == contact_details_value


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "contact_details_type, old_value, new_value",
    [
        ("url", "http://example.com/", "http://new-link.com/"),
        ("email_address", "old@example.com", "new@example.com"),
        ("phone_number", "020 3451 9002", "020 3451 9001"),
    ],
)
def test_send_files_by_email_contact_details_updates_contact_details_and_redirects_to_settings_page(
    client_request,
    service_one,
    mock_update_service,
    mock_get_service_settings_page_common,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    contact_details_type,
    old_value,
    new_value,
):
    service_one["contact_link"] = old_value

    page = client_request.post(
        "main.send_files_by_email_contact_details",
        service_id=SERVICE_ONE_ID,
        _data={
            "contact_details_type": contact_details_type,
            contact_details_type: new_value,
        },
        _follow_redirects=True,
    )
    # no idea why its trying to assert `Settings` as the title when the code says `
    # Send files by email` in our case NL Bestanden per e-mail verzenden
    assert page.select_one("h1").text == "Settings"
    mock_update_service.assert_called_once_with(SERVICE_ONE_ID, contact_link=new_value)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_send_files_by_email_contact_details_uses_the_selected_field_when_multiple_textboxes_contain_data(
    client_request,
    service_one,
    mock_update_service,
    mock_get_service_settings_page_common,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
):
    service_one["contact_link"] = "http://www.old-url.com"

    page = client_request.post(
        "main.send_files_by_email_contact_details",
        service_id=SERVICE_ONE_ID,
        _data={
            "contact_details_type": "url",
            "url": "http://www.new-url.com",
            "email_address": "me@example.com",
            "phone_number": "0207 123 4567",
        },
        _follow_redirects=True,
    )

    assert page.select_one("h1").text == "Settings"
    mock_update_service.assert_called_once_with(SERVICE_ONE_ID, contact_link="http://www.new-url.com")


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "contact_link, subheader, button_selected",
    [
        ("contact.me@gov.uk", "Change contact details for the file download page", True),
        (None, "Add contact details to the file download page", False),
    ],
)
def test_send_files_by_email_contact_details_page(
    client_request, service_one, active_user_with_permissions, contact_link, subheader, button_selected
):
    service_one["contact_link"] = contact_link
    page = client_request.get("main.send_files_by_email_contact_details", service_id=SERVICE_ONE_ID)
    assert normalize_spaces(page.select("h2")[0].text) == subheader
    if button_selected:
        assert "checked" in page.select_one("input[name=contact_details_type][value=email_address]").attrs
    else:
        assert "checked" not in page.select_one("input[name=contact_details_type][value=email_address]").attrs


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_send_files_by_email_contact_details_displays_error_message_when_no_radio_button_selected(
    client_request, service_one
):
    page = client_request.post(
        "main.send_files_by_email_contact_details",
        service_id=SERVICE_ONE_ID,
        _data={
            "contact_details_type": None,
            "url": "",
            "email_address": "",
            "phone_number": "",
        },
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == "Error: Select an option"
    assert normalize_spaces(page.select_one("h1").text) == "Send files by email"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "contact_details_type, invalid_value, error",
    [
        ("url", "invalid.com/", "Enter a URL in the correct format"),
        ("email_address", "me@co", "Enter an email address in the correct format, like name@example.gov.uk"),
        ("phone_number", "abcde", "Enter a phone number in the correct format"),
    ],
)
def test_send_files_by_email_contact_details_does_not_update_invalid_contact_details(
    client_request,
    service_one,
    contact_details_type,
    invalid_value,
    error,
    mocker,
):
    service_one["contact_link"] = "http://example.com/"

    page = client_request.post(
        "main.send_files_by_email_contact_details",
        service_id=SERVICE_ONE_ID,
        _data={
            "contact_details_type": contact_details_type,
            contact_details_type: invalid_value,
        },
        _follow_redirects=True,
    )

    assert error in page.select_one(".govuk-error-message").text
    assert normalize_spaces(page.select_one("h1").text) == "Send files by email"


class TestSetAuthType:
    def test_page_requires_manage_settings_permission(
        self,
        client_request,
        service_one,
        active_user_view_permissions,
    ):
        client_request.login(active_user_view_permissions)
        client_request.get(
            "main.service_set_auth_type",
            service_id=SERVICE_ONE_ID,
            _expected_status=403,
        )

    def test_page_loads(
        self,
        client_request,
        service_one,
        mocker,
    ):
        mocker.patch("app.models.user.Users._get_items")
        page = client_request.get(
            "main.service_set_auth_type",
            service_id=SERVICE_ONE_ID,
        )
        assert page.select_one("form")

    def test_current_setting_selected(
        self,
        client_request,
        service_one,
        mocker,
    ):
        mocker.patch("app.models.user.Users._get_items")
        page = client_request.get(
            "main.service_set_auth_type",
            service_id=SERVICE_ONE_ID,
        )
        radio_items = page.select(".govuk-radios__item")
        assert normalize_spaces(radio_items[0].select_one("label").text) == "Text message code"
        assert radio_items[0].select_one("input").has_attr("checked")
        assert normalize_spaces(radio_items[1].select_one("label").text) == "Email link or text message code"
        assert not radio_items[1].select_one("input").has_attr("checked")

    def tests_redirects_to_set_auth_type_for_users_on_success(
        self,
        client_request,
        service_one,
        mocker,
    ):
        mock_update_service = mocker.patch("app.notify_client.service_api_client.service_api_client.update_service")
        mocker.patch("app.models.user.Users._get_items")
        client_request.post(
            "main.service_set_auth_type",
            service_id=SERVICE_ONE_ID,
            _data={"sign_in_method": SIGN_IN_METHOD_TEXT_OR_EMAIL},
            _expected_redirect=url_for(".service_set_auth_type_for_users", service_id=service_one["id"]),
        )
        assert mock_update_service.call_count == 1
        mock_update_call = mock_update_service.call_args_list[0]
        assert mock_update_call[0] == (service_one["id"],)
        assert set(mock_update_call[1]["permissions"]) == {"email_auth", "email", "sms"}

    def test_redirects_to_confirmation_when_disabling_email_auth(
        self,
        client_request,
        service_one,
        active_user_with_permissions,
        mocker,
    ):
        service_one["permissions"] += ["email_auth"]
        mocker.patch("app.notify_client.service_api_client.service_api_client.update_service")
        mocker.patch("app.models.user.Users._get_items", return_value=[active_user_with_permissions])
        client_request.post(
            "main.service_set_auth_type",
            service_id=SERVICE_ONE_ID,
            _data={"sign_in_method": SIGN_IN_METHOD_TEXT},
            _expected_redirect=url_for(".service_confirm_disable_email_auth", service_id=service_one["id"]),
        )

    def test_cannot_disable_email_auth_if_some_users_dont_have_a_mobile_number(
        self,
        client_request,
        service_one,
        active_user_with_permissions,
        mocker,
    ):
        active_user_with_permissions["mobile_number"] = None
        mocker.patch("app.models.user.Users._get_items", return_value=[active_user_with_permissions])
        service_one["permissions"] += ["email_auth"]
        mocker.patch("app.notify_client.service_api_client.service_api_client.update_service")
        page = client_request.get("main.service_set_auth_type", service_id=SERVICE_ONE_ID)
        assert active_user_with_permissions["name"] in page.select_one("main").text
        assert not page.select_one("main form")


class TestConfirmDisableEmailAuth:
    def test_page_requires_manage_settings_permission(
        self,
        client_request,
        service_one,
        active_user_view_permissions,
    ):
        client_request.login(active_user_view_permissions)
        client_request.get(
            "main.service_confirm_disable_email_auth",
            service_id=SERVICE_ONE_ID,
            _expected_status=403,
        )

    def test_page_loads(
        self,
        client_request,
        service_one,
        active_user_with_permissions,
        mocker,
    ):
        service_one["permissions"] += ["email_auth"]
        mocker.patch("app.models.user.Users._get_items", return_value=[active_user_with_permissions])
        client_request.get(
            "main.service_confirm_disable_email_auth",
            service_id=SERVICE_ONE_ID,
        )

    def test_page_redirects_to_set_auth_type_if_service_doesnt_use_email_auth(
        self,
        client_request,
        service_one,
        active_user_with_permissions,
        mocker,
    ):
        mocker.patch("app.models.user.Users._get_items", return_value=[active_user_with_permissions])
        client_request.get(
            "main.service_confirm_disable_email_auth",
            service_id=SERVICE_ONE_ID,
            _expected_redirect=url_for(".service_set_auth_type", service_id=service_one["id"]),
        )

    def test_redirects_to_set_auth_type_if_some_users_dont_have_mobile_number(
        self,
        client_request,
        service_one,
        active_user_with_permissions,
        mocker,
    ):
        active_user_with_permissions["mobile_number"] = None
        mocker.patch("app.models.user.Users._get_items", return_value=[active_user_with_permissions])
        client_request.get(
            "main.service_confirm_disable_email_auth",
            service_id=SERVICE_ONE_ID,
            _expected_redirect=url_for(".service_set_auth_type", service_id=service_one["id"]),
        )

    def test_save_redirects_to_service_settings(
        self,
        client_request,
        service_one,
        active_user_with_permissions,
        mocker,
    ):
        service_one["permissions"] += ["email_auth"]
        mocker.patch(
            "app.models.user.Users._get_items",
            return_value=[active_user_with_permissions],
        )
        mocker.patch("app.notify_client.service_api_client.service_api_client.update_service")
        client_request.post(
            "main.service_confirm_disable_email_auth",
            service_id=SERVICE_ONE_ID,
            _expected_redirect=url_for(".service_settings", service_id=service_one["id"]),
        )

    def test_save_disables_email_auth_for_service_users(
        self,
        client_request,
        service_one,
        active_user_with_permissions,
        mock_update_user_attribute,
        mocker,
    ):
        active_user_with_permissions["auth_type"] = "email_auth"
        active_user_with_permissions["permissions"][service_one["id"]].append("email_auth")
        mock_update_service = mocker.patch("app.notify_client.service_api_client.service_api_client.update_service")
        mock_update_user = mocker.patch("app.notify_client.user_api_client.user_api_client.update_user_attribute")
        mocker.patch("app.models.user.Users._get_items", return_value=[active_user_with_permissions])
        service_one["permissions"] += ["email_auth"]
        client_request.post(
            "main.service_confirm_disable_email_auth",
            service_id=SERVICE_ONE_ID,
            _expected_redirect=url_for(".service_settings", service_id=service_one["id"]),
        )
        assert mock_update_service.call_count == 1
        mock_update_call = mock_update_service.call_args_list[0]
        assert mock_update_call[0] == (service_one["id"],)
        assert set(mock_update_call[1]["permissions"]) == {"email", "sms"}

        assert mock_update_user.call_args_list == [
            mocker.call(active_user_with_permissions["id"], auth_type="sms_auth")
        ]

    def test_save_does_not_disable_webauthn_sign_in_for_service_users(
        self,
        client_request,
        service_one,
        active_user_with_permissions,
        mocker,
    ):
        active_user_with_permissions["auth_type"] = "webauthn_auth"
        mocker.patch("app.notify_client.service_api_client.service_api_client.update_service")
        mocker.patch("app.models.user.Users._get_items", return_value=[active_user_with_permissions])
        mock_update_user = mocker.patch("app.notify_client.user_api_client.user_api_client.update_user_attribute")
        service_one["permissions"] += ["email_auth"]
        client_request.post(
            "main.service_confirm_disable_email_auth",
            service_id=SERVICE_ONE_ID,
            _expected_redirect=url_for(".service_settings", service_id=service_one["id"]),
        )

        assert mock_update_user.call_args_list == []


class TestSetAuthTypeForUsers:
    def test_requires_manage_settings_permission(
        self,
        client_request,
        service_one,
        active_user_view_permissions,
    ):
        client_request.login(active_user_view_permissions)
        client_request.get(
            "main.service_set_auth_type_for_users",
            service_id=SERVICE_ONE_ID,
            _expected_status=403,
        )

    def test_page_redirects_to_set_auth_type_if_service_cant_email_auth(
        self,
        client_request,
        service_one,
        active_user_with_permissions,
    ):
        client_request.login(active_user_with_permissions)
        client_request.get(
            "main.service_set_auth_type_for_users",
            service_id=SERVICE_ONE_ID,
            _expected_status=302,
            _expected_redirect=url_for(".service_set_auth_type", service_id=service_one["id"]),
        )

    def test_redirects_away_if_no_other_users(
        self,
        client_request,
        service_one,
        active_user_with_permissions,
        mock_get_users_by_service,
        mocker,
    ):
        mocker.patch("app.models.user.InvitedUsers._get_items", return_value=[])

        service_one["permissions"] += ["email_auth"]
        client_request.login(active_user_with_permissions)
        client_request.get(
            "main.service_set_auth_type_for_users",
            service_id=SERVICE_ONE_ID,
            _expected_redirect=url_for(".service_settings", service_id=service_one["id"]),
        )

    def test_page_loads(
        self,
        client_request,
        service_one,
        active_user_with_permissions,
        mock_get_users_by_service,
        mock_get_invites_for_service,
    ):
        service_one["permissions"] += ["email_auth"]
        client_request.login(active_user_with_permissions)
        client_request.get(
            "main.service_set_auth_type_for_users",
            service_id=SERVICE_ONE_ID,
            _follow_redirects=False,
            _expected_status=200,
        )

    def test_page_shows_other_users_on_service(
        self,
        client_request,
        service_one,
        active_user_with_permissions,
        sample_invite,
        mocker,
    ):
        mocker.patch(
            "app.models.user.Users._get_items",
            return_value=[
                create_service_one_user(
                    id="a", name="Alpha", email_address="notify+1@notify.test", auth_type="sms_auth"
                ),
                create_service_one_user(
                    id="b", name="Zulu", email_address="notify+2@notify.test", auth_type="email_auth"
                ),
            ],
        )
        mocker.patch(
            "app.models.user.InvitedUsers._get_items",
            return_value=[sample_invite],
        )
        service_one["permissions"] += ["email_auth"]
        client_request.login(active_user_with_permissions)
        page = client_request.get(
            "main.service_set_auth_type_for_users",
            service_id=SERVICE_ONE_ID,
        )

        # Listed alphabetically by name (or email address for invites)
        labels = page.select("main .govuk-checkboxes label")
        assert [label.text.strip() for label in labels] == [
            "Alpha",
            "invited_user@test.gov.uk",
            "Zulu",
        ]

    def test_sets_email_auth_for_users(
        self,
        client_request,
        service_one,
        active_user_with_permissions,
        mock_get_invites_for_service,
        mock_update_user_attribute,
        mocker,
    ):
        mocker.patch(
            "app.models.user.Users._get_items",
            return_value=[
                create_service_one_user(
                    id="a", name="Alpha", email_address="notify+1@notify.test", auth_type="sms_auth"
                ),
                create_service_one_user(
                    id="b", name="Zulu", email_address="notify+2@notify.test", auth_type="email_auth"
                ),
            ],
        )
        service_one["permissions"] += ["email_auth"]
        client_request.login(active_user_with_permissions)
        client_request.post(
            "main.service_set_auth_type_for_users",
            service_id=SERVICE_ONE_ID,
            _data={"users": ["a", "b"]},
        )

        assert mock_update_user_attribute.call_args_list == [mocker.call("a", auth_type="email_auth")]

    def test_sets_sms_auth_for_deselected_users(
        self,
        client_request,
        service_one,
        active_user_with_permissions,
        mock_get_invites_for_service,
        mock_update_user_attribute,
        mocker,
    ):
        mocker.patch(
            "app.models.user.Users._get_items",
            return_value=[
                create_service_one_user(
                    id="a", name="Alpha", email_address="notify+1@notify.test", auth_type="sms_auth"
                ),
                create_service_one_user(
                    id="b", name="Zulu", email_address="notify+2@notify.test", auth_type="email_auth"
                ),
            ],
        )
        service_one["permissions"] += ["email_auth"]
        client_request.login(active_user_with_permissions)
        client_request.post(
            "main.service_set_auth_type_for_users",
            service_id=SERVICE_ONE_ID,
            # If we don't send any data at all, wtforms doesn't override the defaults (ie it won't recognise us
            # 'unchecking' user b. In reality we will always have a csrf token present, so this should be OK.
            _data={"csrf": "token"},
        )

        assert mock_update_user_attribute.call_args_list == [mocker.call("b", auth_type="sms_auth")]

    def test_updates_invited_users(
        self,
        client_request,
        service_one,
        active_user_with_permissions,
        sample_invite,
        mocker,
    ):
        mocker.patch(
            "app.models.user.Users._get_items",
            return_value=[],
        )
        mocker.patch(
            "app.models.user.InvitedUsers._get_items",
            return_value=[sample_invite],
        )
        mock_update_invite = mocker.patch("app.invite_api_client.update_invite", autospec=True)
        service_one["permissions"] += ["email_auth"]
        client_request.login(active_user_with_permissions)
        client_request.post(
            "main.service_set_auth_type_for_users",
            service_id=SERVICE_ONE_ID,
            _data={"users": [USER_ONE_ID]},
        )

        assert mock_update_invite.call_args_list == [
            mocker.call(service_id=SERVICE_ONE_ID, invite_id=USER_ONE_ID, auth_type="email_auth")
        ]

    @pytest.mark.parametrize(
        "form_data, should_fail",
        (
            ({"users": ["a"]}, False),  # Change user a to email_auth
            ({"users": []}, False),  # Change both user a and user b to sms_auth
            ({"users": ["c"]}, True),  # Change user c to email_auth
        ),
    )
    def test_user_with_webauthn_auth_not_listed_or_editable(
        self,
        client_request,
        service_one,
        active_user_with_permissions,
        mock_get_invites_for_service,
        form_data,
        should_fail,
        mock_update_user_attribute,
        mocker,
    ):
        mocker.patch(
            "app.models.user.Users._get_items",
            return_value=[
                create_service_one_user(
                    id="a", name="Alpha", email_address="notify+1@notify.test", auth_type="sms_auth"
                ),
                create_service_one_user(
                    id="b", name="Beta", email_address="notify+2@notify.test", auth_type="email_auth"
                ),
                create_service_one_user(
                    id="c", name="Charlie", email_address="notify+3@notify.test", auth_type="webauthn_auth"
                ),
            ],
        )
        service_one["permissions"] += ["email_auth"]
        client_request.login(active_user_with_permissions)
        page = client_request.post(
            "main.service_set_auth_type_for_users",
            service_id=SERVICE_ONE_ID,
            _data={"csrf": "token", **form_data},
            _expected_status=200 if should_fail else 302,
        )

        if should_fail:
            assert "not a valid choice for this field" in page.text
            assert mock_update_user_attribute.call_args_list == []
        else:
            assert mock_update_user_attribute.call_args_list != []


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_service_settings_page_loads_when_inbound_number_is_not_set(
    client_request,
    single_reply_to_email_address,
    single_sms_sender,
    mock_no_inbound_number_for_service,
    mock_get_service_data_retention,
):
    client_request.get(
        "main.service_settings",
        service_id=SERVICE_ONE_ID,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_service_receive_text_messages_when_inbound_number_is_not_set(
    client_request,
    mock_no_inbound_number_for_service,
):
    page = client_request.get(
        "main.service_receive_text_messages",
        service_id=SERVICE_ONE_ID,
    )

    assert page.select_one("h1").text == "Receive text messages"
    assert (
        normalize_spaces(page.select("main p")[0].text)
        == "If you want to receive text messages, Notify will give you a unique 11-digit phone number."
    )

    button = page.select_one("a.govuk-button")
    assert normalize_spaces(button.text) == "Start receiving text messages"
    assert button["href"] == url_for(".service_receive_text_messages_start", service_id=SERVICE_ONE_ID)


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "service_has_api_key, expected_paragraphs",
    [
        (
            True,
            [
                "Your service will receive text messages sent to:",
                "You can see the number of received messages on your dashboard.",
                "You can also download the last 7 days’ worth of received text messages.",
                "If you’re using the API, you can fetch received messages or set up a "
                "callback to push the message to your service.",
                "You can still send text messages from a sender ID if you need to, but people "
                "will not be able to reply to those messages.",
                "Stop receiving text messages",
            ],
        ),
        (
            False,
            [
                "Your service will receive text messages sent to:",
                "You can see the number of received messages on your dashboard.",
                "You can also download the last 7 days’ worth of received text messages.",
                "You can still send text messages from a sender ID if you need to, but people "
                "will not be able to reply to those messages.",
                "Stop receiving text messages",
            ],
        ),
    ],
)
def test_service_receive_text_messages_when_inbound_number_is_set(
    client_request,
    service_one,
    mocker,
    service_has_api_key,
    expected_paragraphs,
    mock_get_service_data_retention,
):
    service_one["permissions"] = ["inbound_sms"]
    mocker.patch(
        "app.inbound_number_client.get_inbound_sms_number_for_service", return_value={"data": {"number": "07700900123"}}
    )
    mocker.patch(
        "app.models.service.Service.api_keys",
        new_callable=PropertyMock,
        return_value=service_has_api_key,
    )

    page = client_request.get(
        "main.service_receive_text_messages",
        service_id=SERVICE_ONE_ID,
    )
    paragraphs = page.select("main p")

    assert len(paragraphs) == len(expected_paragraphs)

    for index, p in enumerate(expected_paragraphs):
        assert normalize_spaces(paragraphs[index].text) == p

    assert normalize_spaces(page.select_one(".govuk-inset-text").text) == "07700900123"
    stop_link = page.select_one("a.govuk-link--destructive")
    assert stop_link["href"] == url_for(".service_receive_text_messages_stop", service_id=SERVICE_ONE_ID)


def test_service_receive_text_messages_start_redirects_if_inbound_sms_already_on(
    client_request,
    service_one,
):
    service_one["permissions"] = ["inbound_sms"]

    client_request.get(
        ".service_receive_text_messages_start",
        service_id=SERVICE_ONE_ID,
        _expected_redirect=url_for(".service_receive_text_messages", service_id=SERVICE_ONE_ID),
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_get_service_receive_text_messages_start_shows_details(client_request, mock_get_service_data_retention):
    page = client_request.get(".service_receive_text_messages_start", service_id=SERVICE_ONE_ID)

    assert page.select_one("h1").text == "Before you start receiving text messages"
    assert "The messages you receive will only be available to download for 7 days." in page.text
    assert normalize_spaces(page.select_one(".page-footer button").text) == "I understand – continue"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_post_service_receive_text_messages_start_turns_on_feature_and_redirects(
    client_request,
    mocker,
    service_one,
    mock_update_service,
    active_user_with_permissions,
):
    service_one["permissions"] = []

    mock_add_number = mocker.patch(
        "app.inbound_number_client.add_inbound_number_to_service",
        return_value={"id": "abcd", "service_id": SERVICE_ONE_ID, "inbound_number_id": "1234"},
    )
    mock_event = mocker.patch("app.main.views_nl.service_settings.index.Events.set_inbound_sms_on")

    page = client_request.post(
        ".service_receive_text_messages_start", service_id=SERVICE_ONE_ID, _follow_redirects=True
    )

    mock_add_number.assert_called_once_with(SERVICE_ONE_ID)
    mock_update_service.assert_called_once_with(SERVICE_ONE_ID, permissions=["inbound_sms"])
    mock_event.assert_called_once_with(
        user_id=active_user_with_permissions["id"], service_id=SERVICE_ONE_ID, inbound_number_id="1234"
    )

    assert page.select_one("h1").text == "Receive text messages"
    assert "You added a phone number to your service." in page.text


def test_service_receive_text_messages_stop_redirects_if_inbound_sms_not_enabled(client_request):
    client_request.get(
        ".service_receive_text_messages_stop",
        service_id=SERVICE_ONE_ID,
        _expected_redirect=url_for(".service_receive_text_messages", service_id=SERVICE_ONE_ID),
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_service_receive_text_messages_stop(client_request, service_one, mock_get_inbound_number_for_service):
    service_one["permissions"] = ["inbound_sms"]

    page = client_request.get(
        ".service_receive_text_messages_stop",
        service_id=SERVICE_ONE_ID,
    )

    assert page.select_one("h1").text == "When you stop receiving text messages"
    assert normalize_spaces(page.select_one(".govuk-inset-text").text) == "07812398712"
    assert "You can make 07812398712 the default sender again at any time." in page.text

    support_link = page.select("p a")[-1]
    assert support_link["href"] == url_for(".support")


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_service_receive_text_messages_stop_platform_admin(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_inbound_number_for_service,
    mock_get_most_recent_inbound_usage_date,
):
    service_one["permissions"] = ["inbound_sms"]
    client_request.login(platform_admin_user)

    page = client_request.get(
        ".service_receive_text_messages_stop",
        service_id=SERVICE_ONE_ID,
    )

    assert "This number was last used" in page.text
    radios = page.select("input[type=radio]")
    assert len(radios) == 2

    assert radios[0]["value"] == "true"
    assert radios[1]["value"] == "false"
    assert normalize_spaces(page.select("form button")[0].text) == "Save"


def test_service_receive_text_messages_stop_user_is_not_platform_admin(
    client_request,
    service_one,
    mock_get_inbound_number_for_service,
):
    service_one["permissions"] = ["inbound_sms"]

    page = client_request.get(
        ".service_receive_text_messages_stop",
        service_id=SERVICE_ONE_ID,
    )

    assert "This number was last used" not in page.text
    support_link = page.select("p a")[-1]
    assert support_link["href"] == url_for(".support")


def test_service_receive_text_messages_stop_success_redirect(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_inbound_number_for_service,
    multiple_sms_senders_with_diff_default,
    mocker,
):
    service_one["permissions"] = ["inbound_sms"]
    client_request.login(platform_admin_user)

    mock_remove_service_inbound_sms = mocker.patch("app.service_api_client.remove_service_inbound_sms")

    client_request.post(
        ".service_receive_text_messages_stop",
        service_id=SERVICE_ONE_ID,
        _data={"removal_options": "true"},
        _expected_redirect=url_for(
            ".service_receive_text_messages_stop_success", service_id=SERVICE_ONE_ID, inbound_number="07812398712"
        ),
    )

    mock_remove_service_inbound_sms.assert_called_once_with(SERVICE_ONE_ID, True)


def service_receive_text_messages_stop_success(
    client_request,
    platform_admin_user,
    service_one,
):
    service_one["permissions"] = ["inbound_sms"]
    client_request.login(platform_admin_user)

    page = client_request.get(
        ".service_receive_text_messages_stop_success",
        service_id=SERVICE_ONE_ID,
        inbound_number="07812398712",
    )

    assert page.select_one("h1").text == "You’ve stopped receiving text messages"

    inset_text = page.select_one(".govuk-inset-text")
    assert inset_text and normalize_spaces(inset_text.text) == "07812398712"

    service_settings_link = page.select_one("a.govuk-link")
    assert service_settings_link["href"] == url_for("main.service_settings", service_id=SERVICE_ONE_ID)
    assert "Back to service settings" in service_settings_link.text


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_service_receive_text_messages_stop_handles_error(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_inbound_number_for_service,
    mock_get_most_recent_inbound_usage_date,
    multiple_sms_senders_with_diff_default,
    mocker,
):
    service_one["permissions"] = ["inbound_sms"]
    client_request.login(platform_admin_user)

    mock_remove_service_inbound_sms = mocker.patch(
        "app.service_api_client.remove_service_inbound_sms",
        side_effect=Exception("Failed to process the request"),
    )

    page = client_request.post(
        ".service_receive_text_messages_stop",
        service_id=SERVICE_ONE_ID,
        _data={"removal_options": "true"},
        _expected_status=200,
    )

    mock_remove_service_inbound_sms.assert_called_once_with(SERVICE_ONE_ID, True)

    error_summary = page.select_one(".govuk-error-summary")
    assert error_summary is not None
    assert "There is a problem" in error_summary.text
    assert "Failed to remove number from service" in error_summary.text

    radios = page.select("input[type=radio]")
    assert len(radios) == 2
    assert radios[0]["value"] == "true"
    assert radios[1]["value"] == "false"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_service_receive_text_messages_stop_fails_when_inbound_number_is_default_sender(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_inbound_number_for_service,
    mock_get_most_recent_inbound_usage_date,
    multiple_sms_senders,
    mocker,
):
    service_one["permissions"] = ["inbound_sms"]
    client_request.login(platform_admin_user)

    page = client_request.post(
        ".service_receive_text_messages_stop",
        service_id=SERVICE_ONE_ID,
        _data={"removal_options": "true"},
        _expected_status=200,
    )

    error_summary = page.select_one(".govuk-error-summary")
    assert error_summary is not None
    assert "There is a problem" in error_summary.text
    assert "You need to change your default text message sender ID before you can continue" in error_summary.text

    radios = page.select("input[type=radio]")
    assert len(radios) == 2
    assert radios[0]["value"] == "true"
    assert radios[1]["value"] == "false"


def test_show_sms_prefixing_setting_page(
    client_request,
    mock_update_service,
):
    page = client_request.get("main.service_set_sms_prefix", service_id=SERVICE_ONE_ID)
    assert normalize_spaces(page.select_one("legend").text) == "Start all text messages with ‘service one:’"
    radios = page.select("input[type=radio]")
    assert len(radios) == 2
    assert radios[0]["value"] == "True"
    assert radios[0]["checked"] == ""
    assert radios[1]["value"] == "False"
    with pytest.raises(KeyError):
        assert radios[1]["checked"]


@pytest.mark.parametrize(
    "post_value",
    [
        True,
        False,
    ],
)
def test_updates_sms_prefixing(
    client_request,
    mock_update_service,
    post_value,
):
    client_request.post(
        "main.service_set_sms_prefix",
        service_id=SERVICE_ONE_ID,
        _data={"enabled": post_value},
        _expected_redirect=url_for(
            "main.service_settings",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        prefix_sms=post_value,
    )


def test_select_organisation(
    client_request, platform_admin_user, service_one, mock_get_organisation, mock_get_organisations
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        ".link_service_to_organisation",
        service_id=service_one["id"],
    )

    assert len(page.select(".govuk-radios__item")) == 3
    for i in range(3):
        assert normalize_spaces(page.select(".govuk-radios__item label")[i].text) == f"Org {i + 1}"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_select_organisation_shows_message_if_no_orgs(
    client_request, platform_admin_user, service_one, mock_get_organisation, mocker
):
    mocker.patch("app.organisations_client.get_organisations", return_value=[])

    client_request.login(platform_admin_user)
    page = client_request.get(
        ".link_service_to_organisation",
        service_id=service_one["id"],
    )

    assert normalize_spaces(page.select_one("main p").text) == "No organisations"
    assert not page.select_one("main button")


def test_update_service_organisation(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_organisation,
    mock_get_organisations,
    mock_update_service_organisation,
    mock_update_service,
):
    client_request.login(platform_admin_user)
    client_request.post(
        ".link_service_to_organisation",
        service_id=service_one["id"],
        _data={"organisations": "7aa5d4e9-4385-4488-a489-07812ba13384"},
    )
    mock_update_service_organisation.assert_called_once_with(service_one["id"], "7aa5d4e9-4385-4488-a489-07812ba13384")
    mock_update_service.assert_called_once_with(service_one["id"], has_active_go_live_request=False)


def test_update_service_organisation_sets_daily_sms_limit_to_zero_for_trial_mode_gp(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_organisation_nhs_gp,
    mock_get_organisations,
    mock_update_service_organisation,
    mock_update_service,
):
    service_one["restricted"] = True
    client_request.login(platform_admin_user)
    client_request.post(
        ".link_service_to_organisation",
        service_id=service_one["id"],
        _data={"organisations": "7aa5d4e9-4385-4488-a489-07812ba13384"},
    )
    mock_update_service_organisation.assert_called_once_with(service_one["id"], "7aa5d4e9-4385-4488-a489-07812ba13384")
    assert mock_update_service.call_args_list == [
        call(service_one["id"], sms_message_limit=0),
        call(service_one["id"], has_active_go_live_request=False),
    ]


def test_update_service_organisation_doesnt_change_daily_sms_limit_for_live_gp(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_organisation_nhs_gp,
    mock_get_organisations,
    mock_update_service_organisation,
    mock_update_service,
):
    service_one["restricted"] = False
    client_request.login(platform_admin_user)
    client_request.post(
        ".link_service_to_organisation",
        service_id=service_one["id"],
        _data={"organisations": "7aa5d4e9-4385-4488-a489-07812ba13384"},
    )
    mock_update_service_organisation.assert_called_once_with(service_one["id"], "7aa5d4e9-4385-4488-a489-07812ba13384")
    mock_update_service.assert_called_once_with(service_one["id"], has_active_go_live_request=False)


def test_update_service_organisation_does_not_update_if_same_value(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_organisation,
    mock_get_organisations,
    mock_update_service_organisation,
):
    org_id = "7aa5d4e9-4385-4488-a489-07812ba13383"
    service_one["organisation"] = org_id
    client_request.login(platform_admin_user)
    client_request.post(
        ".link_service_to_organisation",
        service_id=service_one["id"],
        _data={"organisations": org_id},
    )
    assert mock_update_service_organisation.called is False


def test_service_settings_links_to_branding_request_page_for_emails(
    service_one,
    client_request,
    no_reply_to_email_addresses,
    single_sms_sender,
    mock_get_service_data_retention,
):
    # expect to have a "NHS" option as well as the
    # fallback one, so ask user to choose
    service_one["organisation_type"] = "nhs_central"

    page = client_request.get(".service_settings", service_id=SERVICE_ONE_ID)
    assert len(page.select(f'a[href="/services/{SERVICE_ONE_ID}/service-settings/email-branding"]')) == 1


def test_service_settings_links_to_branding_options_page_for_letters(
    service_one,
    client_request,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    mock_get_service_data_retention,
    mocker,
):
    service_one["permissions"].append("letter")
    page = client_request.get(".service_settings", service_id=SERVICE_ONE_ID)
    assert len(page.select(f'a[href="/services/{SERVICE_ONE_ID}/service-settings/letter-branding"]')) == 1


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_show_service_data_retention(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_service_data_retention,
):
    mock_get_service_data_retention.return_value[0]["days_of_retention"] = 5

    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.data_retention",
        service_id=service_one["id"],
    )

    rows = page.select(".govuk-summary-list__row")
    assert len(rows) == 1
    assert normalize_spaces(rows[0].text) == "Email 5 days Change email data retention setting"

    assert page.select_one(".govuk-back-link")["href"] == url_for(
        "main.service_settings",
        service_id=SERVICE_ONE_ID,
    )


def test_view_add_service_data_retention(
    client_request,
    platform_admin_user,
    service_one,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.add_data_retention",
        service_id=service_one["id"],
    )
    assert normalize_spaces(page.select_one("input")["value"]) == "email"
    assert page.select_one("input", attrs={"name": "days_of_retention"})

    assert page.select_one(".govuk-back-link")["href"] == url_for(
        "main.data_retention",
        service_id=SERVICE_ONE_ID,
    )


def test_add_service_data_retention(
    client_request, platform_admin_user, service_one, mock_create_service_data_retention
):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.add_data_retention",
        service_id=service_one["id"],
        _data={"notification_type": "email", "days_of_retention": 5},
        _expected_redirect=url_for(
            "main.data_retention",
            service_id=service_one["id"],
        ),
    )
    assert mock_create_service_data_retention.called


def test_update_service_data_retention(
    client_request,
    platform_admin_user,
    service_one,
    fake_uuid,
    mock_get_service_data_retention,
    mock_update_service_data_retention,
):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.edit_data_retention",
        service_id=service_one["id"],
        data_retention_id=str(fake_uuid),
        _data={"days_of_retention": 5},
        _expected_redirect=url_for(
            "main.data_retention",
            service_id=service_one["id"],
        ),
    )
    assert mock_update_service_data_retention.called


def test_update_service_data_retention_return_validation_error_for_negative_days_of_retention(
    client_request,
    platform_admin_user,
    service_one,
    fake_uuid,
    mock_get_service_data_retention,
    mock_update_service_data_retention,
):
    client_request.login(platform_admin_user)
    page = client_request.post(
        "main.edit_data_retention",
        service_id=service_one["id"],
        data_retention_id=fake_uuid,
        _data={"days_of_retention": -5},
        _expected_status=200,
    )
    assert "The number of days must be between 3 and 90" in page.select_one(".govuk-error-message").text
    assert mock_get_service_data_retention.called
    assert not mock_update_service_data_retention.called


def test_update_service_data_retention_populates_form(
    client_request,
    platform_admin_user,
    service_one,
    fake_uuid,
    mock_get_service_data_retention,
):
    mock_get_service_data_retention.return_value[0]["days_of_retention"] = 5
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.edit_data_retention",
        service_id=service_one["id"],
        data_retention_id=fake_uuid,
    )
    assert page.select_one("input", attrs={"name": "days_of_retention"})["value"] == "5"


def test_service_settings_links_to_edit_service_notes_page_for_platform_admins(
    service_one,
    client_request,
    platform_admin_user,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    mock_get_service_settings_page_common,
    mocker,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        ".service_settings",
        service_id=SERVICE_ONE_ID,
    )
    assert len(page.select(f'a[href="/services/{SERVICE_ONE_ID}/notes"]')) == 1


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_view_edit_service_notes(
    client_request,
    platform_admin_user,
    service_one,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.edit_service_notes",
        service_id=SERVICE_ONE_ID,
    )
    assert page.select_one("h1").text == "Edit service notes"
    assert page.select_one(".govuk-label").text.strip() == "Notes"
    assert page.select_one("textarea").attrs["name"] == "notes"


def test_update_service_notes(client_request, platform_admin_user, service_one, mock_update_service):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.edit_service_notes",
        service_id=SERVICE_ONE_ID,
        _data={"notes": "Very fluffy"},
        _expected_redirect=url_for(
            "main.service_settings",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_update_service.assert_called_with(SERVICE_ONE_ID, notes="Very fluffy")


def test_service_settings_links_to_edit_service_billing_details_page_for_platform_admins(
    service_one,
    client_request,
    platform_admin_user,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    mock_get_service_settings_page_common,
    mocker,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        ".service_settings",
        service_id=SERVICE_ONE_ID,
    )
    assert len(page.select(f'a[href="/services/{SERVICE_ONE_ID}/edit-billing-details"]')) == 1


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_view_edit_service_billing_details(
    client_request,
    platform_admin_user,
    service_one,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.edit_service_billing_details",
        service_id=SERVICE_ONE_ID,
    )

    assert page.select_one("h1").text == "Change billing details"
    assert [label.text.strip() for label in page.select("label.govuk-label") + page.select("label.form-label")] == [
        "Contact names",
        "Contact email addresses",
        "Reference",
        "Purchase order number",
        "Notes",
    ]
    assert [
        form_element["name"]
        for form_element in page.select("input.govuk-input.govuk-\\!-width-full") + page.select("textarea")
    ] == [
        "billing_contact_names",
        "billing_contact_email_addresses",
        "billing_reference",
        "purchase_order_number",
        "notes",
    ]


def test_update_service_billing_details(client_request, platform_admin_user, service_one, mock_update_service):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.edit_service_billing_details",
        service_id=SERVICE_ONE_ID,
        _data={
            "billing_contact_email_addresses": "accounts@fluff.gov.uk",
            "billing_contact_names": "Flannellette von Fluff",
            "billing_reference": "",
            "purchase_order_number": "PO1234",
            "notes": "very fluffy, give extra allowance",
        },
        _expected_redirect=url_for(
            "main.service_settings",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_update_service.assert_called_with(
        SERVICE_ONE_ID,
        billing_contact_email_addresses="accounts@fluff.gov.uk",
        billing_contact_names="Flannellette von Fluff",
        billing_reference="",
        purchase_order_number="PO1234",
        notes="very fluffy, give extra allowance",
    )


@pytest.mark.parametrize("branding_choice", [None, "govuk_and_org", "something_else"])
def test_should_set_default_org_email_branding_fails_if_branding_choice_is_not_org(
    client_request, mocker, branding_choice
):
    organisation = organisation_json(email_branding_id=None, organisation_type="local")
    service = service_json(organisation_id=organisation["id"], organisation_type="local")
    mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[service, service_json(id_="5678", restricted=True)],
    )

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation)
    g.current_service = Service(service)

    assert _should_set_default_org_email_branding(branding_choice) is False


def test_should_set_default_org_email_branding_fails_if_org_already_has_a_default_branding(client_request, mocker):
    organisation = organisation_json(email_branding_id="12345", organisation_type="local")
    service = service_json(organisation_id=organisation["id"], organisation_type="local")
    mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[service, service_json(id_="5678", restricted=True)],
    )

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation)
    g.current_service = Service(service)

    assert _should_set_default_org_email_branding("organisation") is False


def test_should_set_default_org_email_branding_fails_if_org_is_central(client_request, mocker):
    organisation = organisation_json(email_branding_id=None, organisation_type="central")
    service = service_json(organisation_id=organisation["id"], organisation_type="central")
    mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[service, service_json(id_="5678", restricted=True)],
    )

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation)
    g.current_service = Service(service)

    assert _should_set_default_org_email_branding("organisation") is False


def test_should_set_default_org_email_branding_fails_if_other_live_services_in_org(client_request, mocker):
    organisation = organisation_json(email_branding_id=None, organisation_type="local")
    service = service_json(organisation_id=organisation["id"], organisation_type="local")
    mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[service, service_json(id_="5678", restricted=False)],
    )

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation)
    g.current_service = Service(service)

    assert _should_set_default_org_email_branding("organisation") is False


# regardless of whether this service is live, we're only interested in other services with
# different ids when checking for other live services
@pytest.mark.parametrize("is_service_trial", [True, False])
def test_should_set_default_org_email_branding_succeeds_if_all_conditions_are_met(
    client_request, mocker, is_service_trial
):
    organisation = organisation_json(email_branding_id=None, organisation_type="local")
    service = service_json(organisation_id=organisation["id"], organisation_type="local", restricted=is_service_trial)
    mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[service, service_json(id_="5678", restricted=True)],
    )

    mocker.patch("app.organisations_client.get_organisation", return_value=organisation)
    g.current_service = Service(service)

    assert _should_set_default_org_email_branding("organisation") is True


class TestServiceEmailSenderChange:
    @pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
    @pytest.mark.parametrize(
        "custom_email_sender_name, expected_value, expected_conditional_content",
        [
            (
                "custom sender name",
                "True",
                "Sender name custom sender name custom.sender.name@notifications.service.gov.uk",
            ),
            (
                None,
                "False",
                "Sender name Example example@notifications.service.gov.uk",
            ),
        ],
    )
    def test_service_email_sender_change_page_shows_your_current_email_sender_name(
        self,
        client_request,
        service_one,
        custom_email_sender_name,
        expected_value,
        expected_conditional_content,
    ):
        service_one["custom_email_sender_name"] = custom_email_sender_name
        service_one["email_sender_local_part"] = "local.part"
        page = client_request.get("main.service_email_sender_change", service_id=SERVICE_ONE_ID, _expected_status=200)
        assert page.select_one("h1").text == "Email sender name"
        assert [normalize_spaces(radio.text) for radio in page.select(".govuk-radios__item")] == [
            "Use the name of your service service one service.one@notifications.service.gov.uk",
            "Enter a custom sender name",
        ]
        assert page.select_one("input[name=use_custom_email_sender_name][checked]")["value"] == expected_value
        assert normalize_spaces(page.select_one(".govuk-radios__conditional").text) == expected_conditional_content
        custom_preview = page.select_one(
            "#conditional-use_custom_email_sender_name-1 .govuk-hint[data-notify-module=update-status]"
        )
        assert custom_preview["data-target"] == "custom_email_sender_name"
        assert page.select_one("input#custom_email_sender_name[type=text]")
        assert custom_preview["data-updates-url"] == url_for(
            "main.service_email_sender_preview", service_id=SERVICE_ONE_ID
        )

    @pytest.mark.parametrize(
        "custom_email_sender_name, error_message",
        [
            ("", "Error: Enter a sender name"),
            (".", "Sender name must include at least 2 letters or numbers"),
            ("GOV.UK Ειδοποίηση", "Sender name cannot include characters from a non-Latin alphabet"),
            ("no reply", "Sender name needs to be more specific"),
            ("NO-REPLY", "Sender name needs to be more specific"),
            ("info", "Sender name needs to be more specific"),
            ("Support", "Sender name needs to be more specific"),
            ("ALERT", "Sender name needs to be more specific"),
            ("test@example.com", "Sender name cannot be an email address"),
            ("Foo.BAR@example.gov.uk", "Sender name cannot be an email address"),
            # under the 255 db col length, but too long when combined with email_sender_local_part to make an email
            ("a" * 150 + " " * 100 + "a", "Sender name cannot be longer than 143 characters"),
        ],
    )
    def test_service_email_sender_change_fails_if_new_name_fails_validation(
        self, client_request, mock_update_service, custom_email_sender_name, error_message
    ):
        page = client_request.post(
            "main.service_email_sender_change",
            service_id=SERVICE_ONE_ID,
            _data={"use_custom_email_sender_name": "True", "custom_email_sender_name": custom_email_sender_name},
            _expected_status=200,
        )
        assert not mock_update_service.called
        assert error_message in page.select_one(".govuk-error-message").text

    @pytest.mark.parametrize(
        "custom_email_sender_name",
        [
            # Minimum allowable length
            ("eg"),
            # Maximum allowable length
            ("a" * 143),
            # At symbol is allowed as long as the name isn’t an email address
            ("Example@Foo"),
        ],
    )
    def test_service_email_sender_change_updates_service(
        self,
        client_request,
        mock_update_service,
        custom_email_sender_name,
    ):
        client_request.post(
            "main.service_email_sender_change",
            service_id=SERVICE_ONE_ID,
            _data={
                "use_custom_email_sender_name": "True",
                "custom_email_sender_name": custom_email_sender_name,
            },
            _expected_redirect=url_for(
                "main.service_settings",
                service_id=SERVICE_ONE_ID,
            ),
        )
        mock_update_service.assert_called_once_with(
            SERVICE_ONE_ID,
            custom_email_sender_name=custom_email_sender_name,
        )

    @pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
    @pytest.mark.parametrize(
        "custom_email_sender_name, expected_preview",
        [
            ("", "Example<br> example@notifications.service.gov.uk"),
            (".", ".<br> example@notifications.service.gov.uk"),
            ("Custom Name", "Custom Name<br> custom.name@notifications.service.gov.uk"),
            ("GOV.UK Ειδοποίηση", "GOV.UK Ειδοποίηση<br> gov.uk.ειδοποιηση@notifications.service.gov.uk"),
            (
                "<script>alert()</script>",
                "&lt;script&gt;alert()&lt;/script&gt;<br> scriptalertscript@notifications.service.gov.uk",
            ),
            # This example isn’t valid but we still preview it
            ("test@example.com", "test@example.com<br> testexample.com@notifications.service.gov.uk"),
        ],
    )
    def test_service_preview_email_sender_name(self, client_request, custom_email_sender_name, expected_preview):
        response = client_request.post_response(
            "main.service_email_sender_preview",
            service_id=SERVICE_ONE_ID,
            _data={"custom_email_sender_name": custom_email_sender_name},
            _expected_status=200,
        )
        assert normalize_spaces(response.get_json()["html"]) == expected_preview

    @pytest.mark.parametrize(
        "use_custom_email_sender_name, custom_email_sender_name, expected_custom_email_sender_name",
        [
            ("False", "", None),
            # don't validate sender name if the use flag is false
            ("False", "GOV.UK Ειδοποίηση", None),
            ("True", "GOV.UK Notify", "GOV.UK Notify"),
        ],
    )
    def test_service_email_sender_change_should_redirect_on_success(
        self,
        client_request,
        mock_update_service,
        use_custom_email_sender_name,
        custom_email_sender_name,
        expected_custom_email_sender_name,
    ):
        client_request.post(
            "main.service_email_sender_change",
            service_id=SERVICE_ONE_ID,
            _data={
                "use_custom_email_sender_name": use_custom_email_sender_name,
                "custom_email_sender_name": custom_email_sender_name,
            },
            _expected_status=302,
            _expected_redirect=url_for(
                "main.service_settings",
                service_id=SERVICE_ONE_ID,
            ),
        )

        mock_update_service.assert_called_once_with(
            SERVICE_ONE_ID, custom_email_sender_name=expected_custom_email_sender_name
        )

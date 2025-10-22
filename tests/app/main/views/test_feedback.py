import datetime
from functools import partial
from unittest.mock import ANY, PropertyMock

import pytest
from flask import url_for
from freezegun import freeze_time
from notifications_utils.clients.zendesk.zendesk_client import (
    NotifySupportTicket,
    NotifySupportTicketComment,
    NotifyTicketType,
    ZendeskError,
)

from app.constants import ZendeskTopicId
from app.main.views.feedback import ZENDESK_USER_LOGGED_OUT_NOTE, in_business_hours
from app.models.feedback import PROBLEM_TICKET_TYPE, QUESTION_TICKET_TYPE
from tests.conftest import SERVICE_ONE_ID, normalize_spaces, set_config_values


def no_redirect():
    return lambda: None


def test_get_support_index_page(
    client_request,
):
    page = client_request.get(".support")
    assert page.select_one("form")["method"] == "post"
    assert "action" not in page.select_one("form")
    assert normalize_spaces(page.select_one("h1").text) == "Support"
    assert normalize_spaces(page.select_one("form label[for=support_type-0]").text) == "Report a problem"
    assert page.select_one("form input#support_type-0")["value"] == PROBLEM_TICKET_TYPE
    assert normalize_spaces(page.select_one("form label[for=support_type-1]").text) == "Ask a question or give feedback"
    assert page.select_one("form input#support_type-1")["value"] == QUESTION_TICKET_TYPE
    assert normalize_spaces(page.select_one("form button").text) == "Continue"


def test_get_support_index_page_when_signed_out(
    client_request,
):
    client_request.logout()
    page = client_request.get(".support")
    assert page.select_one("form")["method"] == "post"
    assert "action" not in page.select_one("form")
    assert normalize_spaces(page.select_one("form label[for=who-0]").text) == (
        "I work in the public sector and need to send emails, text messages or letters"
    )
    assert page.select_one("form input#who-0")["value"] == "public-sector"
    assert normalize_spaces(page.select_one("form label[for=who-1]").text) == (
        "I’m a member of the public with a question for the government"
    )
    assert page.select_one("form input#who-1")["value"] == "public"
    assert normalize_spaces(page.select_one("form button").text) == "Continue"


def test_choose_question_support_type_shows_feedback_form(
    client_request, mock_get_non_empty_organisations_and_services_for_user, mocker
):
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=True)
    page = client_request.post(
        "main.support",
        _data={"support_type": QUESTION_TICKET_TYPE},
        _follow_redirects=True,
    )
    assert page.select_one("h1").string.strip() == "Ask a question or give feedback"
    assert not page.select_one("input[name=name]")
    assert not page.select_one("input[name=email_address]")
    assert page.select_one("form").find("p").text.strip() == "We’ll reply to test@user.gov.uk"


def test_choose_problem_support_type_shows_problem_type_form(
    client_request, mock_get_non_empty_organisations_and_services_for_user, mocker
):
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=True)
    page = client_request.post(
        "main.support",
        _data={"support_type": PROBLEM_TICKET_TYPE},
        _follow_redirects=True,
    )
    assert page.select_one("h1").string.strip() == "Report a problem"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support")
    assert page.select("form input[type=radio]")[0]["value"] == "sending-messages"
    assert page.select("form input[type=radio]")[1]["value"] == "something-else"


def test_get_support_as_someone_in_the_public_sector(
    client_request,
    mocker,
):
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=True)
    client_request.logout()
    page = client_request.post(
        "main.support",
        _data={"who": "public-sector"},
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select("h1")) == "What do you want to do?"
    assert normalize_spaces(page.select_one("form label[for=support_type-0]").text) == "Report a problem"
    assert page.select_one("form input#support_type-0")["value"] == PROBLEM_TICKET_TYPE
    assert normalize_spaces(page.select_one("form label[for=support_type-1]").text) == "Ask a question or give feedback"
    assert page.select_one("form input#support_type-1")["value"] == QUESTION_TICKET_TYPE
    assert normalize_spaces(page.select_one("form button").text) == "Continue"


def test_get_support_as_member_of_public(
    client_request,
):
    client_request.logout()
    page = client_request.post(
        "main.support",
        _data={"who": "public"},
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select("h1")) == "GOV.UK Notify is for people who work in the government"
    assert len(page.select("h2 a")) == 2
    assert not page.select("form")
    assert not page.select("input")
    assert not page.select("form button")


def test_get_support_what_do_you_want_to_do_page(client_request):
    client_request.logout()
    page = client_request.get("main.support_what_do_you_want_to_do")
    assert normalize_spaces(page.select("h1")) == "What do you want to do?"
    assert normalize_spaces(page.select_one("form label[for=support_type-0]").text) == "Report a problem"
    assert page.select_one("form input#support_type-0")["value"] == PROBLEM_TICKET_TYPE
    assert normalize_spaces(page.select_one("form label[for=support_type-1]").text) == "Ask a question or give feedback"
    assert page.select_one("form input#support_type-1")["value"] == QUESTION_TICKET_TYPE
    assert normalize_spaces(page.select_one("form button").text) == "Continue"


@pytest.mark.parametrize(
    "form_option, redirect_endpoint, redirect_kwargs",
    [
        (PROBLEM_TICKET_TYPE, "main.support_problem", {}),
        (QUESTION_TICKET_TYPE, "main.feedback", {"ticket_type": QUESTION_TICKET_TYPE}),
    ],
)
def test_support_what_do_you_want_to_do_page_redirects(client_request, form_option, redirect_endpoint, redirect_kwargs):
    client_request.logout()
    client_request.post(
        "main.support_what_do_you_want_to_do",
        _data={"support_type": form_option},
        _expected_redirect=url_for(redirect_endpoint, **redirect_kwargs),
    )


def test_support_problem_when_user_is_logged_in(client_request):
    page = client_request.get("main.support_problem")
    assert page.select_one("h1").string.strip() == "Report a problem"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support")

    radios = page.select("form input[type=radio]")
    assert len(radios) == 2
    assert radios[0]["value"] == "sending-messages"
    assert radios[1]["value"] == "something-else"


def test_support_problem_when_user_is_logged_out(client_request):
    client_request.logout()
    page = client_request.get("main.support_problem")
    assert page.select_one("h1").string.strip() == "Report a problem"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support_what_do_you_want_to_do")

    radios = page.select("form input[type=radio]")
    assert len(radios) == 3
    assert radios[0]["value"] == "signing-in"
    assert radios[1]["value"] == "sending-messages"
    assert radios[2]["value"] == "something-else"


@pytest.mark.parametrize(
    "form_option, logged_in, redirect_endpoint, redirect_kwargs",
    [
        ("signing-in", False, "main.support_cannot_sign_in", {}),
        ("sending-messages", True, "main.support_what_happened", {}),
        ("sending-messages", False, "main.support_what_happened", {}),
        (
            "something-else",
            True,
            "main.feedback",
            {"ticket_type": PROBLEM_TICKET_TYPE, "severe": "no", "category": "something-else"},
        ),
        (
            "something-else",
            False,
            "main.feedback",
            {"ticket_type": PROBLEM_TICKET_TYPE, "severe": "no", "category": "something-else"},
        ),
    ],
)
def test_post_support_problem_redirects(client_request, form_option, logged_in, redirect_endpoint, redirect_kwargs):
    if not logged_in:
        client_request.logout()

    client_request.post(
        "main.support_problem",
        _data={"problem_type": form_option},
        _expected_redirect=url_for(redirect_endpoint, **redirect_kwargs),
    )


def test_support_cannot_sign_in(client_request):
    client_request.logout()
    page = client_request.get("main.support_cannot_sign_in")
    assert page.select_one("h1").string.strip() == "Tell us why you cannot sign in"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support_problem")

    radios = page.select("form input[type=radio]")
    assert len(radios) == 5
    assert radios[0]["value"] == "no-code"
    assert radios[1]["value"] == "mobile-number-changed"
    assert radios[2]["value"] == "no-email-link"
    assert radios[3]["value"] == "email-address-changed"
    assert radios[4]["value"] == "something-else"


@pytest.mark.parametrize(
    "form_option, redirect_endpoint, redirect_kwargs",
    [
        ("no-code", "main.support_no_security_code", {}),
        ("mobile-number-changed", "main.support_mobile_number_changed", {}),
        ("no-email-link", "main.support_no_email_link", {}),
        ("email-address-changed", "main.support_email_address_changed", {}),
        (
            "something-else",
            "main.feedback",
            {"ticket_type": PROBLEM_TICKET_TYPE, "severe": "no", "category": "cannot-sign-in"},
        ),
    ],
)
def test_support_cannot_sign_in_redirects(client_request, form_option, redirect_endpoint, redirect_kwargs):
    client_request.logout()

    client_request.post(
        "main.support_cannot_sign_in",
        _data={"sign_in_issue": form_option},
        _expected_redirect=url_for(redirect_endpoint, **redirect_kwargs),
    )


def test_support_no_security_code(client_request):
    client_request.logout()
    page = client_request.get("main.support_no_security_code")
    assert normalize_spaces(page.select_one("h1").text) == "If you did not receive a security code"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support_cannot_sign_in")
    assert page.select_one(f'a[href="{url_for("main.support_no_security_code_account_details")}"]')


def test_support_mobile_number_changed(client_request):
    client_request.logout()
    page = client_request.get("main.support_mobile_number_changed")
    assert normalize_spaces(page.select_one("h1").text) == "If your mobile number has changed"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support_cannot_sign_in")
    assert page.select_one(f'a[href="{url_for("main.support_mobile_number_changed_account_details")}"]')


def test_support_no_email_link(client_request):
    client_request.logout()
    page = client_request.get("main.support_no_email_link")
    assert normalize_spaces(page.select_one("h1").text) == "If you did not receive an email link"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support_cannot_sign_in")
    assert page.select_one(f'a[href="{url_for("main.support_no_email_link_account_details")}"]')


def test_support_email_address_changed(client_request):
    client_request.logout()
    page = client_request.get("main.support_email_address_changed")
    assert normalize_spaces(page.select_one("h1").text) == "If your email address has changed"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support_cannot_sign_in")
    assert page.select_one(f'a[href="{url_for("main.support_email_address_changed_account_details")}"]')


def test_support_no_security_code_account_details_shows_form(client_request):
    client_request.logout()
    page = client_request.get("main.support_no_security_code_account_details")
    assert normalize_spaces(page.select_one("h1").text) == "Enter your account details"

    form_labels = page.select("form label")
    assert len(form_labels) == 3
    assert normalize_spaces(form_labels[0].text) == "Name"
    assert normalize_spaces(form_labels[1].text) == "Email address"
    assert normalize_spaces(form_labels[2].text) == "Mobile number"
    assert normalize_spaces(page.select_one("form button").text) == "Send"


def test_support_no_security_code_account_details_form_requires_all_fields(client_request):
    client_request.logout()
    page = client_request.post(
        "main.support_no_security_code_account_details",
        _data={"name": "", "email_address": "", "mobile_number": ""},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one("#name-error").text) == "Error: Enter your name"
    assert normalize_spaces(page.select_one("#email_address-error").text) == "Error: Enter your email address"
    assert normalize_spaces(page.select_one("#mobile_number-error").text) == "Error: Enter your mobile number"


def test_support_no_security_code_account_details_submits_zendesk_ticket(client_request, mocker):
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mocker.patch(
        "app.main.views.feedback.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )

    client_request.logout()
    page = client_request.post(
        "main.support_no_security_code_account_details",
        _data={"name": "User", "email_address": "test@gov.uk", "mobile_number": "07000000000"},
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Thanks for contacting us"
    mock_create_ticket.assert_called_once_with(
        ANY,
        subject="[env: test] Security code not received",
        message="User did not receive a security code\n\nMobile number: 07000000000",
        ticket_type="incident",
        user_name="User",
        user_email="test@gov.uk",
        notify_ticket_type=None,
        requester_sees_message_content=False,
        custom_topics=[
            {"id": ZendeskTopicId.topic_1, "value": "notify_topic_accessing"},
            {"id": ZendeskTopicId.accessing_notify_1, "value": "notify_accessing_account"},
        ],
    )


def test_support_mobile_number_changed_account_details_shows_form(client_request):
    client_request.logout()
    page = client_request.get("main.support_mobile_number_changed_account_details")
    assert normalize_spaces(page.select_one("h1").text) == "Enter your account details"

    form_labels = page.select("form label")
    assert len(form_labels) == 4
    assert normalize_spaces(form_labels[0].text) == "Name"
    assert normalize_spaces(form_labels[1].text) == "Email address"
    assert normalize_spaces(form_labels[2].text) == "Old mobile number"
    assert normalize_spaces(form_labels[3].text) == "New mobile number"
    assert normalize_spaces(page.select_one("form button").text) == "Send"


def test_support_mobile_number_changed_account_details_form_requires_all_fields(client_request):
    client_request.logout()
    page = client_request.post(
        "main.support_mobile_number_changed_account_details",
        _data={"name": "", "email_address": "", "old_mobile_number": "", "new_mobile_number": ""},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one("#name-error").text) == "Error: Enter your name"
    assert normalize_spaces(page.select_one("#email_address-error").text) == "Error: Enter your email address"
    assert normalize_spaces(page.select_one("#old_mobile_number-error").text) == "Error: Enter your old mobile number"
    assert normalize_spaces(page.select_one("#new_mobile_number-error").text) == "Error: Enter your new mobile number"


def test_support_mobile_number_changed_account_details_submits_zendesk_ticket(client_request, mocker):
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mocker.patch(
        "app.main.views.feedback.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )

    client_request.logout()
    page = client_request.post(
        "main.support_mobile_number_changed_account_details",
        _data={
            "name": "User",
            "email_address": "test@gov.uk",
            "old_mobile_number": "07000000000",
            "new_mobile_number": "07000000001",
        },
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Thanks for contacting us"
    mock_create_ticket.assert_called_once_with(
        ANY,
        subject="[env: test] Change mobile number",
        message="User’s mobile number has changed\n\nOld mobile number: 07000000000\n\nNew mobile number: 07000000001",
        ticket_type="incident",
        user_name="User",
        user_email="test@gov.uk",
        notify_ticket_type=NotifyTicketType.NON_TECHNICAL,
        requester_sees_message_content=False,
        custom_topics=[
            {"id": ZendeskTopicId.topic_1, "value": "notify_topic_accessing"},
            {"id": ZendeskTopicId.accessing_notify_1, "value": "notify_accessing_account"},
            {"id": ZendeskTopicId.topic_2, "value": "notify_topic_accessing_2"},
            {"id": ZendeskTopicId.accessing_notify_2, "value": "notify_accessing_service_2"},
        ],
    )


def test_support_no_email_link_account_details_shows_form(client_request):
    client_request.logout()
    page = client_request.get("main.support_no_email_link_account_details")
    assert normalize_spaces(page.select_one("h1").text) == "Enter your account details"

    form_labels = page.select("form label")
    assert len(form_labels) == 2
    assert normalize_spaces(form_labels[0].text) == "Name"
    assert normalize_spaces(form_labels[1].text) == "Email address"
    assert normalize_spaces(page.select_one("form button").text) == "Send"


def test_support_no_email_link_account_details_form_requires_all_fields(client_request):
    client_request.logout()
    page = client_request.post(
        "main.support_no_email_link_account_details",
        _data={"name": "", "email_address": ""},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one("#name-error").text) == "Error: Enter your name"
    assert normalize_spaces(page.select_one("#email_address-error").text) == "Error: Enter your email address"


def test_support_no_email_link_account_details_submits_zendesk_ticket(client_request, mocker):
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mocker.patch(
        "app.main.views.feedback.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )

    client_request.logout()
    page = client_request.post(
        "main.support_no_email_link_account_details",
        _data={"name": "User", "email_address": "test@gov.uk"},
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Thanks for contacting us"
    mock_create_ticket.assert_called_once_with(
        ANY,
        subject="[env: test] Email link not received",
        message="User did not receive an email link\n\nEmail address: test@gov.uk",
        ticket_type="incident",
        user_name="User",
        user_email="test@gov.uk",
        notify_ticket_type=None,
        requester_sees_message_content=False,
        custom_topics=[
            {"id": ZendeskTopicId.topic_1, "value": "notify_topic_accessing"},
            {"id": ZendeskTopicId.accessing_notify_1, "value": "notify_accessing_account"},
        ],
    )


def test_support_email_address_changed_account_details_shows_form(client_request):
    client_request.logout()
    page = client_request.get("main.support_email_address_changed_account_details")
    assert normalize_spaces(page.select_one("h1").text) == "Enter your account details"

    form_labels = page.select("form label")
    assert len(form_labels) == 3
    assert normalize_spaces(form_labels[0].text) == "Name"
    assert normalize_spaces(form_labels[1].text) == "Old email address"
    assert normalize_spaces(form_labels[2].text) == "New email address"
    assert normalize_spaces(page.select_one("form button").text) == "Send"


def test_support_email_address_changed_account_details_form_requires_all_fields(client_request):
    client_request.logout()
    page = client_request.post(
        "main.support_email_address_changed_account_details",
        _data={"name": "", "old_email_address": "", "new_email_address": ""},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one("#name-error").text) == "Error: Enter your name"
    assert normalize_spaces(page.select_one("#old_email_address-error").text) == "Error: Enter your old email address"
    assert normalize_spaces(page.select_one("#new_email_address-error").text) == "Error: Enter your new email address"


def test_support_email_address_account_details_submits_zendesk_ticket(client_request, mocker):
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mocker.patch(
        "app.main.views.feedback.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )

    client_request.logout()
    page = client_request.post(
        "main.support_email_address_changed_account_details",
        _data={
            "name": "User",
            "old_email_address": "old_address@gov.uk",
            "new_email_address": "new_address@gov.uk",
        },
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Thanks for contacting us"
    mock_create_ticket.assert_called_once_with(
        ANY,
        subject="[env: test] Change email address",
        message=(
            "User’s email address has changed\n\n"
            "Old email address: old_address@gov.uk\n\nNew email address: new_address@gov.uk"
        ),
        ticket_type="incident",
        user_name="User",
        user_email="new_address@gov.uk",
        notify_ticket_type=NotifyTicketType.NON_TECHNICAL,
        requester_sees_message_content=False,
        custom_topics=[
            {"id": ZendeskTopicId.topic_1, "value": "notify_topic_accessing"},
            {"id": ZendeskTopicId.accessing_notify_1, "value": "notify_accessing_account"},
            {"id": ZendeskTopicId.topic_2, "value": "notify_topic_accessing_2"},
            {"id": ZendeskTopicId.accessing_notify_2, "value": "notify_accessing_service_2"},
        ],
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "support_no_security_code",
        "support_mobile_number_changed",
        "support_no_email_link",
        "support_email_address_changed",
        "support_no_security_code_account_details",
        "support_mobile_number_changed_account_details",
        "support_no_email_link_account_details",
        "support_email_address_changed_account_details",
    ],
)
def test_support_sign_in_problem_pages_redirect_if_user_is_logged_in(client_request, endpoint):
    client_request.get(f"main.{endpoint}", _expected_redirect=url_for("main.support_problem"))


@pytest.mark.parametrize("user_logged_in", [True, False])
def test_get_support_what_happened_page(client_request, user_logged_in):
    if not user_logged_in:
        client_request.logout()

    page = client_request.get("main.support_what_happened")
    assert page.select_one("h1").string.strip() == "What happened?"
    assert page.select("form input[type=radio]")[0]["value"] == "technical-difficulties"
    assert page.select("form input[type=radio]")[1]["value"] == "api-500-response"
    assert page.select("form input[type=radio]")[2]["value"] == "something-else"


@pytest.mark.parametrize("user_logged_in", [True, False])
def test_support_what_happened_when_something_else_selected(client_request, user_logged_in):
    if not user_logged_in:
        client_request.logout()

    client_request.post(
        "main.support_what_happened",
        _data={"what_happened": "something-else"},
        _expected_redirect=url_for(
            "main.feedback", ticket_type=PROBLEM_TICKET_TYPE, severe="no", category="problem-sending"
        ),
    )


@pytest.mark.parametrize("error_selected", ["technical-difficulties", "api-500-response"])
@pytest.mark.parametrize(
    "has_live_services, severe, category",
    [
        (True, "yes", "tech-error-live-services"),
        (False, "no", "tech-error-no-live-services"),
    ],
)
def test_support_what_happened_when_an_error_is_selected_and_user_logged_in(
    client_request,
    error_selected,
    has_live_services,
    severe,
    category,
    mocker,
):
    mocker.patch(
        "app.models.user.User.live_services",
        new_callable=PropertyMock,
        return_value=[{}, {}] if has_live_services else [],
    )
    client_request.post(
        "main.support_what_happened",
        _data={"what_happened": error_selected},
        _expected_redirect=url_for("main.feedback", ticket_type=PROBLEM_TICKET_TYPE, severe=severe, category=category),
    )


@pytest.mark.parametrize("error_selected", ["technical-difficulties", "api-500-response"])
def test_support_what_happened_when_an_error_is_selected_and_user_logged_out(
    client_request,
    error_selected,
):
    client_request.logout()
    client_request.post(
        "main.support_what_happened",
        _data={"what_happened": error_selected},
        _expected_redirect=url_for(
            "main.feedback", ticket_type=PROBLEM_TICKET_TYPE, severe="yes", category="tech-error-signed-out"
        ),
    )


@pytest.mark.parametrize(
    "ticket_type, expected_status_code", [(PROBLEM_TICKET_TYPE, 200), (QUESTION_TICKET_TYPE, 200), ("gripe", 404)]
)
def test_get_feedback_page(client_request, mocker, ticket_type, expected_status_code):
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=True)
    client_request.logout()
    client_request.get(
        "main.feedback",
        severe="no",
        ticket_type=ticket_type,
        _expected_status=expected_status_code,
    )


def test_passed_non_logged_in_user_details_through_flow(client_request, mocker):
    client_request.logout()
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=True)
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mock_send_ticket_to_zendesk = mocker.patch(
        "app.main.views.feedback.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
        return_value=1234,
    )
    mock_update_ticket_with_internal_note = mocker.patch(
        "app.main.views.feedback.zendesk_client.update_ticket",
        autospec=True,
    )

    data = {"feedback": "blah", "name": "Anne Example", "email_address": "anne@example.com"}

    client_request.post(
        "main.feedback",
        ticket_type=QUESTION_TICKET_TYPE,
        _data=data,
        _expected_redirect=url_for(
            "main.thanks",
            emergency_ticket=False,
        ),
    )

    mock_create_ticket.assert_called_once_with(
        ANY,
        subject="[env: test] Question or feedback",
        message="blah\n",
        ticket_type="question",
        p1=False,
        user_name="Anne Example",
        user_email="anne@example.com",
        notify_ticket_type=None,
        org_id=None,
        org_type=None,
        service_id=None,
        user_created_at=None,
        custom_topics=None,
    )
    mock_send_ticket_to_zendesk.assert_called_once()
    mock_update_ticket_with_internal_note.assert_called_once_with(
        1234,
        comment=NotifySupportTicketComment(body=ZENDESK_USER_LOGGED_OUT_NOTE, attachments=(), public=False),
    )


def test_does_not_add_internal_note_to_tickets_created_by_suspended_users(client_request, mocker):
    client_request.logout()
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=True)
    mocker.patch(
        "app.main.views.feedback.zendesk_client.send_ticket_to_zendesk",
        return_value=None,
    )
    mock_update_ticket_with_internal_note = mocker.patch("app.main.views.feedback.zendesk_client.update_ticket")

    client_request.post(
        "main.feedback",
        ticket_type=QUESTION_TICKET_TYPE,
        _data={"feedback": "blah", "name": "Anne Example", "email_address": "anne@example.com"},
        _expected_redirect=url_for(
            "main.thanks",
            emergency_ticket=False,
        ),
    )
    assert not mock_update_ticket_with_internal_note.called


def test_does_not_add_internal_note_to_ticket_if_error_creating_ticket(client_request, mocker):
    client_request.logout()
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=True)
    mocker.patch(
        "app.main.views.feedback.zendesk_client.send_ticket_to_zendesk",
        side_effect=ZendeskError("error from Zendesk"),
    )
    mock_update_ticket_with_internal_note = mocker.patch("app.main.views.feedback.zendesk_client.update_ticket")

    with pytest.raises(ZendeskError):
        client_request.post(
            "main.feedback",
            ticket_type=QUESTION_TICKET_TYPE,
            _data={"feedback": "blah", "name": "Anne Example", "email_address": "anne@example.com"},
            _expected_redirect=url_for(
                "main.thanks",
                emergency_ticket=False,
            ),
        )
    assert not mock_update_ticket_with_internal_note.called


@pytest.mark.parametrize(
    "data", [{"feedback": "blah"}, {"feedback": "blah", "name": "Ignored", "email_address": "ignored@email.com"}]
)
@pytest.mark.parametrize(
    "ticket_type, zendesk_ticket_type, expected_subject",
    [
        (PROBLEM_TICKET_TYPE, "incident", "[env: test] Problem"),
        (QUESTION_TICKET_TYPE, "question", "[env: test] Question or feedback"),
    ],
)
def test_passes_user_details_through_flow(
    client_request,
    mock_get_non_empty_organisations_and_services_for_user,
    mocker,
    ticket_type,
    zendesk_ticket_type,
    expected_subject,
    data,
):
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=True)
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mock_send_ticket_to_zendesk = mocker.patch(
        "app.main.views.feedback.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
        return_value=1234,
    )
    mock_update_ticket_with_internal_note = mocker.patch("app.main.views.feedback.zendesk_client.update_ticket")

    client_request.post(
        "main.feedback",
        ticket_type=ticket_type,
        severe="no",
        _data=data,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.thanks",
            emergency_ticket=False,
        ),
    )
    mock_create_ticket.assert_called_once_with(
        ANY,
        subject=expected_subject,
        message=ANY,
        ticket_type=zendesk_ticket_type,
        p1=False,
        user_name="Test User",
        user_email="test@user.gov.uk",
        notify_ticket_type=None,
        org_id=None,
        org_type="central",
        service_id=SERVICE_ONE_ID,
        user_created_at=datetime.datetime(2018, 11, 7, 8, 34, 54, 857402).replace(tzinfo=datetime.UTC),
        custom_topics=None,
    )

    assert mock_create_ticket.call_args[1]["message"] == "\n".join(
        [
            "blah",
            'Service: "service one"',
            url_for(
                "main.service_dashboard",
                service_id=SERVICE_ONE_ID,
                _external=True,
            ),
            "",
        ]
    )
    mock_send_ticket_to_zendesk.assert_called_once()
    assert not mock_update_ticket_with_internal_note.called


def test_zendesk_subject_doesnt_show_env_flag_on_prod(
    notify_admin,
    client_request,
    mock_get_non_empty_organisations_and_services_for_user,
    mocker,
):
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=True)
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mocker.patch(
        "app.main.views.feedback.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )

    with set_config_values(
        notify_admin,
        {
            "NOTIFY_ENVIRONMENT": "production",
            "FEEDBACK_ZENDESK_SUBJECT_PREFIX_ENABLED": False,
        },
    ):
        client_request.post(
            "main.feedback",
            ticket_type=QUESTION_TICKET_TYPE,
            _data={"feedback": "blah"},
            _expected_status=302,
            _expected_redirect=url_for(
                "main.thanks",
                emergency_ticket=False,
            ),
        )

    mock_create_ticket.assert_called_once_with(
        ANY,
        subject="Question or feedback",
        message=ANY,
        ticket_type="question",
        p1=False,
        user_name="Test User",
        user_email="test@user.gov.uk",
        notify_ticket_type=None,
        org_id=None,
        org_type="central",
        service_id=SERVICE_ONE_ID,
        user_created_at=datetime.datetime(2018, 11, 7, 8, 34, 54, 857402).replace(tzinfo=datetime.UTC),
        custom_topics=None,
    )


@pytest.mark.parametrize(
    "ticket_type, category, expected_subject, notify_ticket_type, topics",
    [
        (QUESTION_TICKET_TYPE, None, "Question or feedback", None, None),
        (PROBLEM_TICKET_TYPE, "something-else", "Problem", None, None),
        (PROBLEM_TICKET_TYPE, "problem-sending", "Problem sending messages", None, None),
        (
            PROBLEM_TICKET_TYPE,
            "tech-error-live-services",
            "Urgent - Technical error (live service)",
            NotifyTicketType.TECHNICAL,
            None,
        ),
        (
            PROBLEM_TICKET_TYPE,
            "tech-error-no-live-services",
            "Technical error (no live services)",
            NotifyTicketType.TECHNICAL,
            None,
        ),
        (
            PROBLEM_TICKET_TYPE,
            "tech-error-signed-out",
            "Technical error (user not signed in)",
            NotifyTicketType.TECHNICAL,
            None,
        ),
        (
            PROBLEM_TICKET_TYPE,
            "cannot-sign-in",
            "Cannot sign in",
            None,
            [
                {"id": ZendeskTopicId.topic_1, "value": "notify_topic_accessing"},
                {"id": ZendeskTopicId.accessing_notify_1, "value": "notify_accessing_account"},
            ],
        ),
    ],
)
def test_zendesk_subject_and_ticket_type_reflect_journey_taken_to_support_form(
    notify_admin,
    client_request,
    mock_get_non_empty_organisations_and_services_for_user,
    ticket_type,
    category,
    expected_subject,
    notify_ticket_type,
    topics,
    mocker,
):
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=True)
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mocker.patch(
        "app.main.views.feedback.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )
    client_request.post(
        "main.feedback",
        ticket_type=ticket_type,
        severe="no",
        category=category,
        _data={"feedback": "blah"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.thanks",
            emergency_ticket=False,
        ),
    )
    mock_create_ticket.assert_called_once_with(
        ANY,
        subject=f"[env: test] {expected_subject}",
        message=ANY,
        ticket_type=ANY,
        p1=False,
        user_name="Test User",
        user_email="test@user.gov.uk",
        notify_ticket_type=notify_ticket_type,
        org_id=None,
        org_type="central",
        service_id=SERVICE_ONE_ID,
        user_created_at=datetime.datetime(2018, 11, 7, 8, 34, 54, 857402).replace(tzinfo=datetime.UTC),
        custom_topics=topics,
    )


@pytest.mark.parametrize(
    "ticket_type",
    [
        PROBLEM_TICKET_TYPE,
        QUESTION_TICKET_TYPE,
    ],
)
def test_email_address_required_for_problems_and_questions(
    client_request,
    ticket_type,
    mocker,
):
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=True)
    mocker.patch("app.main.views.feedback.zendesk_client")
    client_request.logout()
    page = client_request.post(
        "main.feedback",
        ticket_type=ticket_type,
        severe="no",
        _data={"feedback": "blah", "name": "Fred"},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one("#email_address-error").text) == "Error: Enter your email address"


@pytest.mark.parametrize(
    "ticket_type",
    [
        PROBLEM_TICKET_TYPE,
        QUESTION_TICKET_TYPE,
    ],
)
def test_name_required_for_problems_and_questions(
    client_request,
    ticket_type,
    mocker,
):
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=True)
    mocker.patch("app.main.views.feedback.zendesk_client")
    client_request.logout()
    page = client_request.post(
        "main.feedback",
        ticket_type=ticket_type,
        severe="no",
        _data={"feedback": "blah", "email_address": "me@gov.uk"},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one("#name-error").text) == "Error: Enter your name"


@pytest.mark.parametrize("ticket_type", (PROBLEM_TICKET_TYPE, QUESTION_TICKET_TYPE))
def test_email_address_must_be_valid_if_provided_to_support_form(
    client_request,
    mocker,
    ticket_type,
):
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=True)
    client_request.logout()
    page = client_request.post(
        "main.feedback",
        ticket_type=ticket_type,
        severe="no",
        _data={
            "feedback": "blah",
            "email_address": "not valid",
        },
        _expected_status=200,
    )

    assert (
        normalize_spaces(page.select_one("#email_address-error").text)
        == "Error: Enter your email address in the correct format, like name@example.gov.uk"
    )


@pytest.mark.parametrize(
    "ticket_type, severe, is_in_business_hours, is_emergency_ticket",
    [
        # business hours, never an emergency
        (PROBLEM_TICKET_TYPE, "yes", True, False),
        (QUESTION_TICKET_TYPE, "yes", True, False),
        (PROBLEM_TICKET_TYPE, "no", True, False),
        (QUESTION_TICKET_TYPE, "no", True, False),
        # out of hours, if the user says it’s not an emergency
        (PROBLEM_TICKET_TYPE, "no", False, False),
        (QUESTION_TICKET_TYPE, "no", False, False),
        # out of hours, only problems can be emergencies
        (PROBLEM_TICKET_TYPE, "yes", False, True),
        (QUESTION_TICKET_TYPE, "yes", False, False),
    ],
)
def test_urgency(
    client_request,
    mock_get_non_empty_organisations_and_services_for_user,
    mocker,
    ticket_type,
    severe,
    is_in_business_hours,
    is_emergency_ticket,
):
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=is_in_business_hours)

    mock_ticket = mocker.patch("app.main.views.feedback.NotifySupportTicket")
    mocker.patch(
        "app.main.views.feedback.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )

    client_request.post(
        "main.feedback",
        ticket_type=ticket_type,
        severe=severe,
        _data={"feedback": "blah", "email_address": "test@example.com"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.thanks",
            emergency_ticket=is_emergency_ticket,
        ),
    )
    assert mock_ticket.call_args[1]["p1"] == is_emergency_ticket

    if is_emergency_ticket:
        assert "See runbook for help resolving" in mock_ticket.call_args[1]["message"]
    else:
        assert "See runbook for help resolving" not in mock_ticket.call_args[1]["message"]


ids, params = zip(
    *[
        (
            "non-logged in users always have to triage out of hours",
            (
                PROBLEM_TICKET_TYPE,
                False,
                False,
                True,
                302,
                partial(url_for, "main.support_problem"),
            ),
        ),
        (
            "non-logged in users always have to triage in hours",
            (
                PROBLEM_TICKET_TYPE,
                True,
                False,
                True,
                302,
                partial(url_for, "main.support_problem"),
            ),
        ),
        ("trial services are never high priority", (PROBLEM_TICKET_TYPE, False, True, False, 200, no_redirect())),
        (
            "problems in hours for live services need triage",
            (PROBLEM_TICKET_TYPE, True, True, True, 302, partial(url_for, "main.support_problem")),
        ),
        (
            "problems in hours for trial services do not need triage",
            (PROBLEM_TICKET_TYPE, True, True, False, 200, no_redirect()),
        ),
        ("only problems are high priority", (QUESTION_TICKET_TYPE, False, True, True, 200, no_redirect())),
        (
            "should triage out of hours",
            (
                PROBLEM_TICKET_TYPE,
                False,
                True,
                True,
                302,
                partial(url_for, "main.support_problem"),
            ),
        ),
    ],
    strict=True,
)


@pytest.mark.parametrize(
    "ticket_type, is_in_business_hours, logged_in, has_live_services,expected_status, expected_redirect",
    params,
    ids=ids,
)
def test_redirects_to_report_a_problem_page(
    client_request,
    mocker,
    ticket_type,
    is_in_business_hours,
    logged_in,
    has_live_services,
    expected_status,
    expected_redirect,
):
    mocker.patch(
        "app.models.user.User.live_services",
        new_callable=PropertyMock,
        return_value=[{}, {}] if has_live_services else [],
    )
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=is_in_business_hours)
    if not logged_in:
        client_request.logout()

    client_request.get(
        "main.feedback",
        ticket_type=ticket_type,
        _expected_status=expected_status,
        _expected_redirect=expected_redirect(),
    )


def test_doesnt_lose_message_if_post_across_closing(
    client_request,
    mocker,
):
    mocker.patch("app.models.user.User.live_services", return_value=True)
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=False)

    page = client_request.post(
        "main.feedback",
        ticket_type=PROBLEM_TICKET_TYPE,
        _data={"feedback": "foo"},
        _expected_status=302,
        _expected_redirect=url_for(".support_problem"),
    )
    with client_request.session_transaction() as session:
        assert session["feedback_message"] == "foo"

    page = client_request.get(
        "main.feedback",
        ticket_type=PROBLEM_TICKET_TYPE,
        severe="yes",
    )

    with client_request.session_transaction() as session:
        assert page.select_one("textarea", {"name": "feedback"}).text in "\r\nfoo"
        assert "feedback_message" not in session


@pytest.mark.parametrize(
    "when, is_in_business_hours",
    [
        ("2016-06-06 09:29:59+0100", False),  # opening time, summer and winter
        ("2016-12-12 09:29:59+0000", False),
        ("2016-06-06 09:30:00+0100", True),
        ("2016-12-12 09:30:00+0000", True),
        ("2016-12-12 12:00:00+0000", True),  # middle of the day
        ("2016-12-12 17:29:59+0000", True),  # closing time
        ("2016-12-12 17:30:00+0000", False),
        ("2016-12-10 12:00:00+0000", False),  # Saturday
        ("2016-12-11 12:00:00+0000", False),  # Sunday
        ("2022-12-27 12:00:00+0000", False),  # Bank holiday - substitute boxing day (Tuesday)
    ],
)
def test_in_business_hours(when, is_in_business_hours):
    with freeze_time(when):
        assert in_business_hours() == is_in_business_hours


@pytest.mark.parametrize(
    "extra_args, ticket_type, expected_back_link",
    [
        (
            {"severe": "yes"},
            PROBLEM_TICKET_TYPE,
            partial(url_for, "main.support"),
        ),
        ({"severe": "no"}, PROBLEM_TICKET_TYPE, partial(url_for, "main.support")),
        ({"severe": "foo"}, QUESTION_TICKET_TYPE, partial(url_for, "main.support")),  # hacking the URL
        ({}, QUESTION_TICKET_TYPE, partial(url_for, "main.support")),
        ({"severe": "no", "category": "something-else"}, PROBLEM_TICKET_TYPE, partial(url_for, "main.support_problem")),
        (
            {"severe": "no", "category": "problem-sending"},
            PROBLEM_TICKET_TYPE,
            partial(url_for, "main.support_what_happened"),
        ),
        (
            {"severe": "yes", "category": "tech-error-live-services"},
            PROBLEM_TICKET_TYPE,
            partial(url_for, "main.support_what_happened"),
        ),
        (
            {"severe": "no", "category": "tech-error-no-live-services"},
            PROBLEM_TICKET_TYPE,
            partial(url_for, "main.support_what_happened"),
        ),
        (
            {"severe": "no", "category": "tech-error-signed-out"},
            PROBLEM_TICKET_TYPE,
            partial(url_for, "main.support_what_happened"),
        ),
    ],
)
def test_back_link_from_form(
    client_request,
    mock_get_non_empty_organisations_and_services_for_user,
    mocker,
    extra_args,
    ticket_type,
    expected_back_link,
):
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=True)
    page = client_request.get("main.feedback", ticket_type=ticket_type, **extra_args)
    assert page.select_one(".govuk-back-link")["href"] == expected_back_link()
    h1 = normalize_spaces(page.select_one("h1").text)

    if ticket_type == PROBLEM_TICKET_TYPE:
        assert h1 == "Describe the problem"
    else:
        assert h1 == "Ask a question or give feedback"


@pytest.mark.parametrize(
    (
        "is_in_business_hours, severe,"
        "expected_status_code, expected_redirect,"
        "expected_status_code_when_logged_in, expected_redirect_when_logged_in"
    ),
    [
        (True, "yes", 200, no_redirect(), 200, no_redirect()),
        (True, "no", 200, no_redirect(), 200, no_redirect()),
        (
            False,
            "no",
            200,
            no_redirect(),
            200,
            no_redirect(),
        ),
        # Treat empty query param as mangled URL – ask question again
        (
            False,
            "",
            302,
            partial(url_for, "main.support_problem"),
            302,
            partial(url_for, "main.support_problem"),
        ),
        # User hasn’t answered the triage question
        (
            False,
            None,
            302,
            partial(url_for, "main.support_problem"),
            302,
            partial(url_for, "main.support_problem"),
        ),
        # Escalation is needed for non-logged-in users
        (
            False,
            "yes",
            302,
            partial(url_for, "main.bat_phone"),
            200,
            no_redirect(),
        ),
    ],
)
def test_should_be_shown_the_bat_email(
    client_request,
    active_user_with_permissions,
    mocker,
    mock_get_non_empty_organisations_and_services_for_user,
    is_in_business_hours,
    severe,
    expected_status_code,
    expected_redirect,
    expected_status_code_when_logged_in,
    expected_redirect_when_logged_in,
):
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=is_in_business_hours)

    feedback_page = url_for("main.feedback", ticket_type=PROBLEM_TICKET_TYPE, severe=severe)

    client_request.logout()
    client_request.get_url(
        feedback_page,
        _expected_status=expected_status_code,
        _expected_redirect=expected_redirect(),
    )

    # logged in users should never be redirected to the bat email page
    client_request.login(active_user_with_permissions)
    client_request.get_url(
        feedback_page,
        _expected_status=expected_status_code_when_logged_in,
        _expected_redirect=expected_redirect_when_logged_in(),
    )


def test_bat_email_page(
    client_request,
    active_user_with_permissions,
):
    bat_phone_page = "main.bat_phone"

    client_request.logout()
    page = client_request.get(bat_phone_page)

    assert page.select_one(".govuk-back-link").text.strip() == "Back"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support")

    page_links = page.select("main a")
    form_link = next(
        filter(
            lambda link: link["href"]
            == url_for("main.feedback", ticket_type=PROBLEM_TICKET_TYPE, category="problem-sending", severe="no"),
            page_links,
        ),
        None,
    )
    assert form_link is not None

    client_request.login(active_user_with_permissions)
    client_request.get(
        bat_phone_page,
        _expected_redirect=url_for("main.feedback", ticket_type=PROBLEM_TICKET_TYPE),
    )


@pytest.mark.parametrize(
    "emergency_ticket, out_of_hours, message",
    (
        # Out of hours emergencies trump everything else
        (
            True,
            True,
            "We’ll reply in the next 30 minutes.",
        ),
        (
            True,
            False,  # Not a real scenario
            "We’ll reply in the next 30 minutes.",
        ),
        # When we look at your ticket depends on whether we’re in normal
        # business hours
        (
            False,
            False,
            "We’ll reply by the end of the next working day.",
        ),
        (False, True, "We’ll reply by the end of the next working day."),
    ),
)
def test_thanks(
    client_request,
    mocker,
    emergency_ticket,
    out_of_hours,
    message,
):
    mocker.patch("app.main.views.feedback.in_business_hours", return_value=(not out_of_hours))
    page = client_request.get(
        "main.thanks",
        emergency_ticket=emergency_ticket,
    )
    assert normalize_spaces(page.select_one("main").find("p").text) == message

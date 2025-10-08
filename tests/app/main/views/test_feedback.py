import datetime
from functools import partial
from unittest.mock import ANY, PropertyMock

import pytest
import pytz
from flask import url_for
from freezegun import freeze_time
from notifications_utils.clients.zendesk.zendesk_client import (
    NotifySupportTicket,
    NotifySupportTicketComment,
    ZendeskError,
)

from app.main.views_nl.feedback import ZENDESK_USER_LOGGED_OUT_NOTE, in_business_hours
from app.models.feedback import (
    GENERAL_TICKET_TYPE,
    PROBLEM_TICKET_TYPE,
    QUESTION_TICKET_TYPE,
)
from tests.conftest import SERVICE_ONE_ID, normalize_spaces, set_config_values


def no_redirect():
    return lambda: None


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_get_support_index_page(
    client_request,
):
    page = client_request.get(".support")
    assert page.select_one("form")["method"] == "post"
    assert "action" not in page.select_one("form")
    assert normalize_spaces(page.select_one("h1").text) == "Support"
    assert normalize_spaces(page.select_one("form label[for=support_type-0]").text) == "Report a problem"
    assert page.select_one("form input#support_type-0")["value"] == "report-problem"
    assert normalize_spaces(page.select_one("form label[for=support_type-1]").text) == "Ask a question or give feedback"
    assert page.select_one("form input#support_type-1")["value"] == "ask-question-give-feedback"
    assert normalize_spaces(page.select_one("form button").text) == "Continue"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
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


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "support_type, expected_h1",
    [
        (PROBLEM_TICKET_TYPE, "Report a problem"),
        (QUESTION_TICKET_TYPE, "Ask a question or give feedback"),
    ],
)
def test_choose_support_type(
    client_request, mock_get_non_empty_organisations_and_services_for_user, mocker, support_type, expected_h1
):
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    page = client_request.post(
        "main.support",
        _data={"support_type": support_type},
        _follow_redirects=True,
    )
    assert page.select_one("h1").string.strip() == expected_h1
    assert not page.select_one("input[name=name]")
    assert not page.select_one("input[name=email_address]")
    assert page.select_one("form").find("p").text.strip() == "We’ll reply to test@user.gov.uk"


def test_get_support_as_someone_in_the_public_sector(
    client_request,
    mocker,
):
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    client_request.logout()
    page = client_request.post(
        "main.support",
        _data={"who": "public-sector"},
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select("h1")) == "Contact GOV.UK Notify support"
    assert page.select_one("form textarea[name=feedback]")
    assert page.select_one("form input[name=name]")
    assert page.select_one("form input[name=email_address]")
    assert page.select_one("form button")


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
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


@pytest.mark.parametrize(
    "ticket_type, expected_status_code", [(PROBLEM_TICKET_TYPE, 200), (QUESTION_TICKET_TYPE, 200), ("gripe", 404)]
)
def test_get_feedback_page(client_request, mocker, ticket_type, expected_status_code):
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    client_request.logout()
    client_request.get(
        "main.feedback",
        ticket_type=ticket_type,
        _expected_status=expected_status_code,
    )


def test_passed_non_logged_in_user_details_through_flow(client_request, mocker):
    client_request.logout()
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mock_send_ticket_to_zendesk = mocker.patch(
        "app.main.views_nl.feedback.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
        return_value=1234,
    )
    mock_update_ticket_with_internal_note = mocker.patch(
        "app.main.views_nl.feedback.zendesk_client.update_ticket",
        autospec=True,
    )

    data = {"feedback": "blah", "name": "Anne Example", "email_address": "anne@example.com"}

    client_request.post(
        "main.feedback",
        ticket_type=GENERAL_TICKET_TYPE,
        _data=data,
        _expected_redirect=url_for(
            "main.thanks",
            out_of_hours_emergency=False,
        ),
    )

    mock_create_ticket.assert_called_once_with(
        ANY,
        subject="[env: test] General Notify Support",
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
    )
    mock_send_ticket_to_zendesk.assert_called_once()
    mock_update_ticket_with_internal_note.assert_called_once_with(
        1234,
        comment=NotifySupportTicketComment(body=ZENDESK_USER_LOGGED_OUT_NOTE, attachments=(), public=False),
    )


def test_does_not_add_internal_note_to_tickets_created_by_suspended_users(client_request, mocker):
    client_request.logout()
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    mocker.patch(
        "app.main.views_nl.feedback.zendesk_client.send_ticket_to_zendesk",
        return_value=None,
    )
    mock_update_ticket_with_internal_note = mocker.patch("app.main.views_nl.feedback.zendesk_client.update_ticket")

    client_request.post(
        "main.feedback",
        ticket_type=GENERAL_TICKET_TYPE,
        _data={"feedback": "blah", "name": "Anne Example", "email_address": "anne@example.com"},
        _expected_redirect=url_for(
            "main.thanks",
            out_of_hours_emergency=False,
        ),
    )
    assert not mock_update_ticket_with_internal_note.called


def test_does_not_add_internal_note_to_ticket_if_error_creating_ticket(client_request, mocker):
    client_request.logout()
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    mocker.patch(
        "app.main.views_nl.feedback.zendesk_client.send_ticket_to_zendesk",
        side_effect=ZendeskError("error from Zendesk"),
    )
    mock_update_ticket_with_internal_note = mocker.patch("app.main.views_nl.feedback.zendesk_client.update_ticket")

    with pytest.raises(ZendeskError):
        client_request.post(
            "main.feedback",
            ticket_type=GENERAL_TICKET_TYPE,
            _data={"feedback": "blah", "name": "Anne Example", "email_address": "anne@example.com"},
            _expected_redirect=url_for(
                "main.thanks",
                out_of_hours_emergency=False,
            ),
        )
    assert not mock_update_ticket_with_internal_note.called


@pytest.mark.parametrize(
    "data", [{"feedback": "blah"}, {"feedback": "blah", "name": "Ignored", "email_address": "ignored@email.com"}]
)
@pytest.mark.parametrize(
    "ticket_type, zendesk_ticket_type, expected_subject",
    [
        (PROBLEM_TICKET_TYPE, "incident", "[env: test] Reported Problem"),
        (QUESTION_TICKET_TYPE, "question", "[env: test] Question/Feedback"),
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
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mock_send_ticket_to_zendesk = mocker.patch(
        "app.main.views_nl.feedback.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
        return_value=1234,
    )
    mock_update_ticket_with_internal_note = mocker.patch("app.main.views_nl.feedback.zendesk_client.update_ticket")

    client_request.post(
        "main.feedback",
        ticket_type=ticket_type,
        _data=data,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.thanks",
            out_of_hours_emergency=False,
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
        user_created_at=datetime.datetime(2018, 11, 7, 8, 34, 54, 857402).replace(tzinfo=pytz.utc),
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
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mocker.patch(
        "app.main.views_nl.feedback.zendesk_client.send_ticket_to_zendesk",
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
            ticket_type=GENERAL_TICKET_TYPE,
            _data={"feedback": "blah"},
            _expected_status=302,
            _expected_redirect=url_for(
                "main.thanks",
                out_of_hours_emergency=False,
            ),
        )

    mock_create_ticket.assert_called_once_with(
        ANY,
        subject="General Notify Support",
        message=ANY,
        ticket_type="question",
        p1=False,
        user_name="Test User",
        user_email="test@user.gov.uk",
        notify_ticket_type=None,
        org_id=None,
        org_type="central",
        service_id=SERVICE_ONE_ID,
        user_created_at=datetime.datetime(2018, 11, 7, 8, 34, 54, 857402).replace(tzinfo=pytz.utc),
    )


@pytest.mark.parametrize(
    "data",
    [
        {"feedback": "blah", "name": "Fred"},
        {"feedback": "blah"},
    ],
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
    mocker,
    data,
    ticket_type,
):
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    mocker.patch("app.main.views_nl.feedback.zendesk_client")
    client_request.logout()
    page = client_request.post("main.feedback", ticket_type=ticket_type, _data=data, _expected_status=200)
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == "Error: Enter your email address"


@pytest.mark.parametrize("ticket_type", (PROBLEM_TICKET_TYPE, QUESTION_TICKET_TYPE))
def test_email_address_must_be_valid_if_provided_to_support_form(
    client_request,
    mocker,
    ticket_type,
):
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    client_request.logout()
    page = client_request.post(
        "main.feedback",
        ticket_type=ticket_type,
        _data={
            "feedback": "blah",
            "email_address": "not valid",
        },
        _expected_status=200,
    )

    assert (
        normalize_spaces(page.select_one(".govuk-error-message").text)
        == "Error: Enter your email address in the correct format, like name@example.gov.uk"
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "ticket_type, severe, is_in_business_hours, is_out_of_hours_emergency",
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
    is_out_of_hours_emergency,
):
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=is_in_business_hours)

    mock_ticket = mocker.patch("app.main.views_nl.feedback.NotifySupportTicket")
    mocker.patch(
        "app.main.views_nl.feedback.zendesk_client.send_ticket_to_zendesk",
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
            out_of_hours_emergency=is_out_of_hours_emergency,
        ),
    )
    assert mock_ticket.call_args[1]["p1"] == is_out_of_hours_emergency

    if is_out_of_hours_emergency:
        assert "See runbook for help resolving" in mock_ticket.call_args[1]["message"]
    else:
        assert "See runbook for help resolving" not in mock_ticket.call_args[1]["message"]


ids, params = zip(
    *[
        (
            "non-logged in users always have to triage",
            (
                GENERAL_TICKET_TYPE,
                False,
                False,
                True,
                302,
                partial(url_for, "main.triage", ticket_type=GENERAL_TICKET_TYPE),
            ),
        ),
        ("trial services are never high priority", (PROBLEM_TICKET_TYPE, False, True, False, 200, no_redirect())),
        ("we can triage in hours", (PROBLEM_TICKET_TYPE, True, True, True, 200, no_redirect())),
        ("only problems are high priority", (QUESTION_TICKET_TYPE, False, True, True, 200, no_redirect())),
        (
            "should triage out of hours",
            (
                PROBLEM_TICKET_TYPE,
                False,
                True,
                True,
                302,
                partial(url_for, "main.triage", ticket_type=PROBLEM_TICKET_TYPE),
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
def test_redirects_to_triage(
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
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=is_in_business_hours)
    if not logged_in:
        client_request.logout()

    client_request.get(
        "main.feedback",
        ticket_type=ticket_type,
        _expected_status=expected_status,
        _expected_redirect=expected_redirect(),
    )


@pytest.mark.parametrize(
    "ticket_type",
    [
        PROBLEM_TICKET_TYPE,
        GENERAL_TICKET_TYPE,
    ],
)
def test_options_on_triage_page(
    client_request,
    ticket_type,
):
    page = client_request.get("main.triage", ticket_type=ticket_type)
    assert normalize_spaces(page.select_one("h1").text) == "Did you get one of the following errors?"
    assert page.select("form input[type=radio]")[0]["value"] == "yes"
    assert page.select("form input[type=radio]")[1]["value"] == "no"


def test_doesnt_lose_message_if_post_across_closing(
    client_request,
    mocker,
):
    mocker.patch("app.models.user.User.live_services", return_value=True)
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=False)

    page = client_request.post(
        "main.feedback",
        ticket_type=PROBLEM_TICKET_TYPE,
        _data={"feedback": "foo"},
        _expected_status=302,
        _expected_redirect=url_for(".triage", ticket_type=PROBLEM_TICKET_TYPE),
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
    "ticket_type",
    (
        GENERAL_TICKET_TYPE,
        PROBLEM_TICKET_TYPE,
    ),
)
@pytest.mark.parametrize(
    "choice, expected_redirect_param",
    [
        ("yes", "yes"),
        ("no", "no"),
    ],
)
def test_triage_redirects_to_correct_url(
    client_request,
    ticket_type,
    choice,
    expected_redirect_param,
):
    client_request.post(
        "main.triage",
        ticket_type=ticket_type,
        _data={"severe": choice},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.feedback",
            ticket_type=ticket_type,
            severe=expected_redirect_param,
        ),
    )


@pytest.mark.parametrize(
    "extra_args, expected_back_link, expected_page_title",
    [
        (
            {"severe": "yes"},
            partial(url_for, "main.triage", ticket_type=PROBLEM_TICKET_TYPE),
            "Tell us about the emergency",
        ),
        ({"severe": "no"}, partial(url_for, "main.triage", ticket_type=PROBLEM_TICKET_TYPE), "Report a problem"),
        ({"severe": "foo"}, partial(url_for, "main.support"), "Report a problem"),  # hacking the URL
        ({}, partial(url_for, "main.support"), "Report a problem"),
    ],
)
def test_back_link_from_form(
    client_request,
    mock_get_non_empty_organisations_and_services_for_user,
    mocker,
    extra_args,
    expected_back_link,
    expected_page_title,
):
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    page = client_request.get("main.feedback", ticket_type=PROBLEM_TICKET_TYPE, **extra_args)
    assert page.select_one(".govuk-back-link")["href"] == expected_back_link()
    assert normalize_spaces(page.select_one("h1").text) == expected_page_title


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
            partial(url_for, "main.triage", ticket_type=PROBLEM_TICKET_TYPE),
            302,
            partial(url_for, "main.triage", ticket_type=PROBLEM_TICKET_TYPE),
        ),
        # User hasn’t answered the triage question
        (
            False,
            None,
            302,
            partial(url_for, "main.triage", ticket_type=PROBLEM_TICKET_TYPE),
            302,
            partial(url_for, "main.triage", ticket_type=PROBLEM_TICKET_TYPE),
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
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=is_in_business_hours)

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


@pytest.mark.parametrize(
    (
        "severe,"
        "expected_status_code, expected_redirect,"
        "expected_status_code_when_logged_in, expected_redirect_when_logged_in"
    ),
    [
        # User hasn’t answered the triage question
        (
            None,
            302,
            partial(url_for, "main.triage", ticket_type=GENERAL_TICKET_TYPE),
            302,
            partial(url_for, "main.triage", ticket_type=GENERAL_TICKET_TYPE),
        ),
        # Escalation is needed for non-logged-in users
        (
            "yes",
            302,
            partial(url_for, "main.bat_phone"),
            200,
            no_redirect(),
        ),
    ],
)
def test_should_be_shown_the_bat_email_for_general_questions(
    client_request,
    active_user_with_permissions,
    mocker,
    mock_get_non_empty_organisations_and_services_for_user,
    severe,
    expected_status_code,
    expected_redirect,
    expected_status_code_when_logged_in,
    expected_redirect_when_logged_in,
):
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=False)

    feedback_page = url_for("main.feedback", ticket_type=GENERAL_TICKET_TYPE, severe=severe)

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
            lambda link: link["href"] == url_for("main.feedback", ticket_type=PROBLEM_TICKET_TYPE, severe="no"),
            page_links,
        ),
        None,
    )
    assert form_link is not None

    client_request.login(active_user_with_permissions)
    client_request.get(bat_phone_page, _expected_redirect=url_for("main.feedback", ticket_type=PROBLEM_TICKET_TYPE))


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "out_of_hours_emergency, out_of_hours, message",
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
    out_of_hours_emergency,
    out_of_hours,
    message,
):
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=(not out_of_hours))
    page = client_request.get(
        "main.thanks",
        out_of_hours_emergency=out_of_hours_emergency,
    )
    assert normalize_spaces(page.select_one("main").find("p").text) == message

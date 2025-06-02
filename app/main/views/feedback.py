from datetime import UTC, datetime

from flask import current_app, redirect, render_template, request, session, url_for
from flask_login import current_user
from notifications_utils.bank_holidays import BankHolidays
from notifications_utils.clients.zendesk.zendesk_client import (
    NotifySupportTicket,
    NotifySupportTicketComment,
    NotifyTicketType,
)
from notifications_utils.timezones import local_timezone

from app import convert_to_boolean, current_service
from app.constants import ZendeskTopicId
from app.extensions import zendesk_client
from app.main import main
from app.main.forms import (
    FeedbackOrProblem,
    SupportEmailAddressChangedForm,
    SupportMobileNumberChangedForm,
    SupportNoEmailLinkForm,
    SupportNoSecurityCodeForm,
    SupportProblemTypeForm,
    SupportRedirect,
    SupportSignInIssuesForm,
    SupportType,
    SupportWhatHappenedForm,
)
from app.models.feedback import PROBLEM_TICKET_TYPE, QUESTION_TICKET_TYPE
from app.utils import hide_from_search_engines

bank_holidays = BankHolidays(use_cached_holidays=True)

ZENDESK_USER_LOGGED_OUT_NOTE = (
    "The requester is not signed in to GOV.UK Notify.\n\n"
    "To confirm they have access to the email address they entered in the support form:\n\n"
    "1. Submit a public reply to this ticket.\n"
    "2. Wait for the requester to reply."
)


@main.route("/support", methods=["GET", "POST"])
@hide_from_search_engines
def support():
    if current_user.is_authenticated:
        form = SupportType()
        if form.validate_on_submit():
            if form.support_type.data == PROBLEM_TICKET_TYPE:
                return redirect(url_for("main.support_problem"))
            else:
                return redirect(
                    url_for(
                        "main.feedback",
                        ticket_type=form.support_type.data,
                    )
                )
    else:
        form = SupportRedirect()
        if form.validate_on_submit():
            if form.who.data == "public":
                return redirect(url_for(".support_public"))
            else:
                return redirect(url_for("main.support_what_do_you_want_to_do"))

    return render_template("views/support/index.html", form=form, error_summary_enabled=True)


@main.route("/support/what-do-you-want-to-do", methods=["GET", "POST"])
@hide_from_search_engines
def support_what_do_you_want_to_do():
    form = SupportType()
    if form.validate_on_submit():
        if form.support_type.data == PROBLEM_TICKET_TYPE:
            return redirect(url_for("main.support_problem"))
        else:
            # ticket type is ask-question-give-feedback
            return redirect(
                url_for(
                    "main.feedback",
                    ticket_type=form.support_type.data,
                )
            )

    return render_template("views/support/what-do-you-want-to-do.html", form=form, error_summary_enabled=True)


@main.route("/support/problem", methods=["GET", "POST"])
@hide_from_search_engines
def support_problem():
    form = SupportProblemTypeForm(user_logged_in=current_user.is_authenticated)

    back_link = url_for(".support") if current_user.is_authenticated else url_for(".support_what_do_you_want_to_do")

    if form.validate_on_submit():
        if form.problem_type.data == "signing-in":
            return redirect(url_for("main.support_cannot_sign_in"))
        elif form.problem_type.data == "sending-messages":
            return redirect(url_for("main.support_what_happened"))
        elif form.problem_type.data == "something-else":
            return redirect(
                url_for(".feedback", ticket_type=PROBLEM_TICKET_TYPE, severe="no", category="something-else")
            )
    return render_template("views/support/problem.html", back_link=back_link, form=form, error_summary_enabled=True)


@main.route("/support/cannot-sign-in", methods=["GET", "POST"])
@hide_from_search_engines
def support_cannot_sign_in():
    form = SupportSignInIssuesForm()

    if form.validate_on_submit():
        if form.sign_in_issue.data == "no-code":
            return redirect(url_for("main.support_no_security_code"))
        elif form.sign_in_issue.data == "mobile-number-changed":
            return redirect(url_for("main.support_mobile_number_changed"))
        elif form.sign_in_issue.data == "no-email-link":
            return redirect(url_for("main.support_no_email_link"))
        elif form.sign_in_issue.data == "email-address-changed":
            return redirect(url_for("main.support_email_address_changed"))
        elif form.sign_in_issue.data == "something-else":
            return redirect(
                url_for("main.feedback", ticket_type=PROBLEM_TICKET_TYPE, severe="no", category="cannot-sign-in")
            )

    return render_template("views/support/cannot-sign-in.html", form=form, error_summary_enabled=True)


@main.route("/support/security-code")
@hide_from_search_engines
def support_no_security_code():
    if current_user.is_authenticated:
        return redirect(url_for("main.support_problem"))

    return render_template("views/support/no-security-code.html")


@main.route("/support/mobile-number-changed")
@hide_from_search_engines
def support_mobile_number_changed():
    if current_user.is_authenticated:
        return redirect(url_for("main.support_problem"))

    return render_template("views/support/mobile-number-changed.html")


@main.route("/support/email-link")
@hide_from_search_engines
def support_no_email_link():
    if current_user.is_authenticated:
        return redirect(url_for("main.support_problem"))

    return render_template("views/support/no-email-link.html")


@main.route("/support/email-address-changed")
@hide_from_search_engines
def support_email_address_changed():
    if current_user.is_authenticated:
        return redirect(url_for("main.support_problem"))

    return render_template("views/support/email-address-changed.html")


def create_sign_in_issues_zendesk_ticket(
    subject,
    message,
    name,
    email,
    notifiy_ticket_type=None,
    service_access_issue=False,
):
    prefix = (
        ""
        if not current_app.config["FEEDBACK_ZENDESK_SUBJECT_PREFIX_ENABLED"]
        else f"[env: {current_app.config['NOTIFY_ENVIRONMENT']}] "
    )

    custom_topics = [
        {"id": ZendeskTopicId.topic_1, "value": "notify_topic_accessing"},
        {"id": ZendeskTopicId.accessing_notify_1, "value": "notify_accessing_account"},
    ]
    if service_access_issue:
        custom_topics += [
            {"id": ZendeskTopicId.topic_2, "value": "notify_topic_accessing_2"},
            {"id": ZendeskTopicId.accessing_notify_2, "value": "notify_accessing_service_2"},
        ]

    ticket = NotifySupportTicket(
        subject=f"{prefix}{subject}",
        message=message,
        ticket_type=get_zendesk_ticket_type(PROBLEM_TICKET_TYPE),
        notify_ticket_type=notifiy_ticket_type,
        user_name=name,
        user_email=email,
        requester_sees_message_content=False,
        custom_topics=custom_topics,
    )
    zendesk_client.send_ticket_to_zendesk(ticket)


@main.route("/support/security-code/account-details", methods=["GET", "POST"])
@hide_from_search_engines
def support_no_security_code_account_details():
    if current_user.is_authenticated:
        return redirect(url_for("main.support_problem"))

    form = SupportNoSecurityCodeForm()

    if form.validate_on_submit():
        feedback_msg = render_template(
            "support-tickets/sign-in-issue-no-security-code.txt",
            user_mobile=form.mobile_number.data,
        )
        create_sign_in_issues_zendesk_ticket(
            subject="Security code not received",
            message=feedback_msg,
            name=form.name.data,
            email=form.email_address.data,
        )

        return redirect(url_for("main.thanks"))

    return render_template("views/support/no-security-code-account-details.html", form=form, error_summary_enabled=True)


@main.route("/support/mobile-number-changed/account-details", methods=["GET", "POST"])
@hide_from_search_engines
def support_mobile_number_changed_account_details():
    if current_user.is_authenticated:
        return redirect(url_for("main.support_problem"))

    form = SupportMobileNumberChangedForm()

    if form.validate_on_submit():
        feedback_msg = render_template(
            "support-tickets/sign-in-issue-mobile-number-changed.txt",
            old_mobile_number=form.old_mobile_number.data,
            new_mobile_number=form.new_mobile_number.data,
        )
        create_sign_in_issues_zendesk_ticket(
            subject="Change mobile number",
            message=feedback_msg,
            name=form.name.data,
            email=form.email_address.data,
            notifiy_ticket_type=NotifyTicketType.NON_TECHNICAL,
            service_access_issue=True,
        )

        return redirect(url_for("main.thanks"))

    return render_template(
        "views/support/mobile-number-changed-account-details.html",
        form=form,
        error_summary_enabled=True,
    )


@main.route("/support/email-link/account-details", methods=["GET", "POST"])
@hide_from_search_engines
def support_no_email_link_account_details():
    if current_user.is_authenticated:
        return redirect(url_for("main.support_problem"))

    form = SupportNoEmailLinkForm()

    if form.validate_on_submit():
        feedback_msg = render_template(
            "support-tickets/sign-in-issue-no-email-link.txt",
            user_email_address=form.email_address.data,
        )
        create_sign_in_issues_zendesk_ticket(
            subject="Email link not received",
            message=feedback_msg,
            name=form.name.data,
            email=form.email_address.data,
        )

        return redirect(url_for("main.thanks"))

    return render_template("views/support/no-email-link-account-details.html", form=form, error_summary_enabled=True)


@main.route("/support/email-address-changed/account-details", methods=["GET", "POST"])
@hide_from_search_engines
def support_email_address_changed_account_details():
    if current_user.is_authenticated:
        return redirect(url_for("main.support_problem"))

    form = SupportEmailAddressChangedForm()

    if form.validate_on_submit():
        feedback_msg = render_template(
            "support-tickets/sign-in-issue-email-address-changed.txt",
            old_email_address=form.old_email_address.data,
            new_email_address=form.new_email_address.data,
        )
        create_sign_in_issues_zendesk_ticket(
            subject="Change email address",
            message=feedback_msg,
            name=form.name.data,
            email=form.new_email_address.data,
            notifiy_ticket_type=NotifyTicketType.NON_TECHNICAL,
            service_access_issue=True,
        )

        return redirect(url_for("main.thanks"))

    return render_template(
        "views/support/email-address-changed-account-details.html",
        form=form,
        error_summary_enabled=True,
    )


@main.route("/support/what-happened", methods=["GET", "POST"])
@hide_from_search_engines
def support_what_happened():
    form = SupportWhatHappenedForm()

    if form.validate_on_submit():
        if form.what_happened.data == "something-else":
            return redirect(
                url_for(".feedback", ticket_type=PROBLEM_TICKET_TYPE, severe="no", category="problem-sending")
            )
        else:
            if current_user.is_authenticated and current_user.live_services:
                severe = "yes"
                category = "tech-error-live-services"
            elif current_user.is_authenticated and not current_user.live_services:
                severe = "no"
                category = "tech-error-no-live-services"
            else:
                severe = "yes"
                category = "tech-error-signed-out"

            return redirect(
                url_for(
                    "main.feedback",
                    ticket_type=PROBLEM_TICKET_TYPE,
                    severe=severe,
                    category=category,
                )
            )

    return render_template("views/support/what-happened.html", form=form, error_summary_enabled=True)


@main.route("/support/public")
@hide_from_search_engines
def support_public():
    return render_template("views/support/public.html")


feedback_page_details = {
    QUESTION_TICKET_TYPE: {
        "default": {"zendesk_subject": "Question or feedback", "back_link": "main.support", "notify_ticket_type": None}
    },
    PROBLEM_TICKET_TYPE: {
        "default": {"zendesk_subject": "Problem", "back_link": "main.support", "notify_ticket_type": None},
        "something-else": {
            "zendesk_subject": "Problem",
            "back_link": "main.support_problem",
            "notify_ticket_type": None,
        },
        "problem-sending": {
            "zendesk_subject": "Problem sending messages",
            "back_link": "main.support_what_happened",
            "notify_ticket_type": None,
        },
        "tech-error-live-services": {
            "zendesk_subject": "Urgent - Technical error (live service)",
            "back_link": "main.support_what_happened",
            "notify_ticket_type": NotifyTicketType.TECHNICAL,
        },
        "tech-error-no-live-services": {
            "zendesk_subject": "Technical error (no live services)",
            "back_link": "main.support_what_happened",
            "notify_ticket_type": NotifyTicketType.TECHNICAL,
        },
        "tech-error-signed-out": {
            "zendesk_subject": "Technical error (user not signed in)",
            "back_link": "main.support_what_happened",
            "notify_ticket_type": NotifyTicketType.TECHNICAL,
        },
        "cannot-sign-in": {
            "zendesk_subject": "Cannot sign in",
            "back_link": "main.support_problem",
            "notify_ticket_type": None,
            "custom_topics": [
                {"id": ZendeskTopicId.topic_1, "value": "notify_topic_accessing"},
                {"id": ZendeskTopicId.accessing_notify_1, "value": "notify_accessing_account"},
            ],
        },
    },
}


@main.route("/support/<ticket_type:ticket_type>", methods=["GET", "POST"])
@hide_from_search_engines
def feedback(ticket_type):
    form = FeedbackOrProblem()

    if not form.feedback.data:
        form.feedback.data = session.pop("feedback_message", "")

    category = request.args.get("category", "default")

    if request.args.get("severe") in ["yes", "no"]:
        severe = convert_to_boolean(request.args.get("severe"))
    else:
        severe = None

    if needs_triage(ticket_type, severe):
        session["feedback_message"] = form.feedback.data
        return redirect(url_for(".support_problem"))

    emergency_ticket = is_emergency_ticket(ticket_type, severe)

    if needs_escalation(ticket_type, severe):
        return redirect(url_for(".bat_phone"))

    if current_user.is_authenticated:
        form.email_address.data = current_user.email_address
        form.name.data = current_user.name

    if form.validate_on_submit():
        user_email = form.email_address.data
        user_name = form.name.data

        feedback_msg = render_template(
            "support-tickets/support-ticket.txt",
            content=form.feedback.data,
            emergency_ticket=emergency_ticket,
        )

        prefix = (
            ""
            if not current_app.config["FEEDBACK_ZENDESK_SUBJECT_PREFIX_ENABLED"]
            else f"[env: {current_app.config['NOTIFY_ENVIRONMENT']}] "
        )

        subject = prefix + feedback_page_details[ticket_type][category]["zendesk_subject"]

        ticket = NotifySupportTicket(
            subject=subject,
            message=feedback_msg,
            ticket_type=get_zendesk_ticket_type(ticket_type),
            notify_ticket_type=feedback_page_details[ticket_type][category]["notify_ticket_type"],
            p1=emergency_ticket,
            user_name=user_name,
            user_email=user_email,
            org_id=current_service.organisation_id if current_service else None,
            org_type=current_service.organisation_type if current_service else None,
            service_id=current_service.id if current_service else None,
            user_created_at=current_user.created_at,
            custom_topics=feedback_page_details[ticket_type][category].get("custom_topics"),
        )
        zendesk_ticket_id = zendesk_client.send_ticket_to_zendesk(ticket)

        if zendesk_ticket_id and not current_user.is_authenticated:
            zendesk_client.update_ticket(
                zendesk_ticket_id,
                comment=NotifySupportTicketComment(body=ZENDESK_USER_LOGGED_OUT_NOTE, public=False),
            )

        return redirect(
            url_for(
                ".thanks",
                emergency_ticket=emergency_ticket,
            )
        )

    page_title = "Describe the problem" if ticket_type == PROBLEM_TICKET_TYPE else "Ask a question or give feedback"
    back_link = url_for(feedback_page_details[ticket_type][category]["back_link"])

    return render_template(
        "views/support/form.html",
        form=form,
        back_link=back_link,
        page_title=page_title,
        error_summary_enabled=True,
    )


@main.route("/support/escalate", methods=["GET", "POST"])
@hide_from_search_engines
def bat_phone():
    if current_user.is_authenticated:
        return redirect(url_for("main.feedback", ticket_type=PROBLEM_TICKET_TYPE))

    return render_template("views/support/bat-phone.html")


@main.route("/support/thanks", methods=["GET", "POST"])
@hide_from_search_engines
def thanks():
    return render_template(
        "views/support/thanks.html",
        emergency_ticket=convert_to_boolean(request.args.get("emergency_ticket")),
        out_of_hours=not in_business_hours(),
    )


def in_business_hours():
    now = datetime.now(UTC)

    if is_weekend(now) or is_bank_holiday(now):
        return False

    return london_time_today_as_utc(9, 30) <= now < london_time_today_as_utc(17, 30)


def london_time_today_as_utc(hour, minute):
    return datetime.now(local_timezone).replace(hour=hour, minute=minute).astimezone(UTC)


def is_weekend(time):
    return time.strftime("%A") in {
        "Saturday",
        "Sunday",
    }


def is_bank_holiday(time):
    return bank_holidays.is_holiday(time.date())


def needs_triage(ticket_type, severe):
    return all(
        (
            ticket_type != QUESTION_TICKET_TYPE,
            severe is None,
            (not current_user.is_authenticated or current_user.live_services),
        )
    )


def needs_escalation(ticket_type, severe):
    return all(
        (
            ticket_type != QUESTION_TICKET_TYPE,
            severe,
            not current_user.is_authenticated,
            not in_business_hours(),
        )
    )


def is_emergency_ticket(ticket_type, severe):
    if ticket_type != PROBLEM_TICKET_TYPE or not severe:
        return False

    if current_user.is_authenticated or not in_business_hours():
        return True

    return False


def get_zendesk_ticket_type(ticket_type):
    # Zendesk has 4 ticket types - "problem", "incident", "task" and "question".
    # We don't want to use a Zendesk "problem" ticket type when someone reports a
    # Notify problem because they are designed to group multiple incident tickets together,
    # allowing them to be solved as a group.
    if ticket_type == PROBLEM_TICKET_TYPE:
        return NotifySupportTicket.TYPE_INCIDENT

    return NotifySupportTicket.TYPE_QUESTION

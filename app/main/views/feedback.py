from datetime import datetime

import pytz
from flask import current_app, redirect, render_template, request, session, url_for
from flask_login import current_user
from notifications_utils.bank_holidays import BankHolidays
from notifications_utils.clients.zendesk.zendesk_client import NotifySupportTicket, NotifySupportTicketComment

from app import convert_to_boolean, current_service
from app.extensions import zendesk_client
from app.main import main
from app.main.forms import FeedbackOrProblem, SupportRedirect, SupportType, Triage
from app.models.feedback import (
    GENERAL_TICKET_TYPE,
    PROBLEM_TICKET_TYPE,
    QUESTION_TICKET_TYPE,
)
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
            return redirect(
                url_for(
                    ".feedback",
                    ticket_type=form.support_type.data,
                )
            )
    else:
        form = SupportRedirect()
        if form.validate_on_submit():
            if form.who.data == "public":
                return redirect(url_for(".support_public"))
            else:
                return redirect(
                    url_for(
                        ".feedback",
                        ticket_type=GENERAL_TICKET_TYPE,
                    )
                )

    return render_template("views/support/index.html", form=form, error_summary_enabled=True)


@main.route("/support/public")
@hide_from_search_engines
def support_public():
    return render_template("views/support/public.html")


@main.route("/support/triage", methods=["GET", "POST"])
@main.route("/support/triage/<ticket_type:ticket_type>", methods=["GET", "POST"])
@hide_from_search_engines
def triage(ticket_type=PROBLEM_TICKET_TYPE):
    form = Triage()
    if form.validate_on_submit():
        return redirect(url_for(".feedback", ticket_type=ticket_type, severe=form.severe.data))
    return render_template("views/support/triage.html", form=form, error_summary_enabled=True)


@main.route("/support/<ticket_type:ticket_type>", methods=["GET", "POST"])
@hide_from_search_engines
def feedback(ticket_type):
    form = FeedbackOrProblem()

    ticket_type_names = {
        GENERAL_TICKET_TYPE: {
            "page_title": "Contact GOV.UK Notify support",
            "ticket_subject": "General Notify Support",
        },
        PROBLEM_TICKET_TYPE: {"page_title": "Report a problem", "ticket_subject": "Reported Problem"},
        QUESTION_TICKET_TYPE: {"page_title": "Ask a question or give feedback", "ticket_subject": "Question/Feedback"},
    }

    if not form.feedback.data:
        form.feedback.data = session.pop("feedback_message", "")

    if request.args.get("severe") in ["yes", "no"]:
        severe = convert_to_boolean(request.args.get("severe"))
    else:
        severe = None

    out_of_hours_emergency = all(
        (
            ticket_type != QUESTION_TICKET_TYPE,
            not in_business_hours(),
            severe,
        )
    )

    if needs_triage(ticket_type, severe):
        session["feedback_message"] = form.feedback.data
        return redirect(url_for(".triage", ticket_type=ticket_type))

    if needs_escalation(ticket_type, severe):
        return redirect(url_for(".bat_phone"))

    if current_user.is_authenticated:
        form.email_address.data = current_user.email_address
        form.name.data = current_user.name

    if form.validate_on_submit():
        user_email = form.email_address.data
        user_name = form.name.data or None

        feedback_msg = render_template(
            "support-tickets/support-ticket.txt",
            content=form.feedback.data,
            out_of_hours_emergency=out_of_hours_emergency,
        )

        prefix = (
            ""
            if not current_app.config["FEEDBACK_ZENDESK_SUBJECT_PREFIX_ENABLED"]
            else f"[env: {current_app.config['NOTIFY_ENVIRONMENT']}] "
        )

        subject = prefix + ticket_type_names[ticket_type]["ticket_subject"]

        ticket = NotifySupportTicket(
            subject=subject,
            message=feedback_msg,
            ticket_type=get_zendesk_ticket_type(ticket_type),
            notify_ticket_type=None,  # don't set technical/non-technical, we'll do this as part of triage on support
            p1=out_of_hours_emergency,
            user_name=user_name,
            user_email=user_email,
            org_id=current_service.organisation_id if current_service else None,
            org_type=current_service.organisation_type if current_service else None,
            service_id=current_service.id if current_service else None,
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
                out_of_hours_emergency=out_of_hours_emergency,
            )
        )

    if severe:
        page_title = "Tell us about the emergency"
    else:
        page_title = ticket_type_names[ticket_type]["page_title"]

    return render_template(
        "views/support/form.html",
        form=form,
        back_link=(url_for(".support") if severe is None else url_for(".triage", ticket_type=ticket_type)),
        show_status_page_banner=(ticket_type == PROBLEM_TICKET_TYPE),
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
        out_of_hours_emergency=convert_to_boolean(request.args.get("out_of_hours_emergency")),
        out_of_hours=not in_business_hours(),
    )


def in_business_hours():
    now = datetime.utcnow().replace(tzinfo=pytz.utc)

    if is_weekend(now) or is_bank_holiday(now):
        return False

    return london_time_today_as_utc(9, 30) <= now < london_time_today_as_utc(17, 30)


def london_time_today_as_utc(hour, minute):
    return (
        pytz.timezone("Europe/London").localize(datetime.now().replace(hour=hour, minute=minute)).astimezone(pytz.utc)
    )


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
            not in_business_hours(),
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


def get_zendesk_ticket_type(ticket_type):
    # Zendesk has 4 ticket types - "problem", "incident", "task" and "question".
    # We don't want to use a Zendesk "problem" ticket type when someone reports a
    # Notify problem because they are designed to group multiple incident tickets together,
    # allowing them to be solved as a group.
    if ticket_type == PROBLEM_TICKET_TYPE:
        return NotifySupportTicket.TYPE_INCIDENT

    return NotifySupportTicket.TYPE_QUESTION

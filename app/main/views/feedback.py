from datetime import datetime

import pytz
from flask import current_app, redirect, render_template, request, session, url_for
from flask_login import current_user
from govuk_bank_holidays.bank_holidays import BankHolidays

from app import convert_to_boolean, current_service, service_api_client
from app.extensions import zendesk_client
from app.main import main
from app.main.forms import (
    FeedbackOrProblem,
    SupportRedirect,
    SupportType,
    Triage,
)
from app.models.feedback import (
    GENERAL_TICKET_TYPE,
    PROBLEM_TICKET_TYPE,
    QUESTION_TICKET_TYPE,
)

bank_holidays = BankHolidays(use_cached_holidays=True)


@main.route('/support', methods=['GET', 'POST'])
def support():

    if current_user.is_authenticated:
        form = SupportType()
        if form.validate_on_submit():
            return redirect(url_for(
                '.feedback',
                ticket_type=form.support_type.data,
            ))
    else:
        form = SupportRedirect()
        if form.validate_on_submit():
            if form.who.data == 'public':
                return redirect(url_for(
                    '.support_public'
                ))
            else:
                return redirect(url_for(
                    '.feedback',
                    ticket_type=GENERAL_TICKET_TYPE,
                ))

    return render_template('views/support/index.html', form=form)


@main.route('/support/public')
def support_public():
    return render_template('views/support/public.html')


@main.route('/support/triage', methods=['GET', 'POST'])
@main.route('/support/triage/<ticket_type:ticket_type>', methods=['GET', 'POST'])
def triage(ticket_type=PROBLEM_TICKET_TYPE):
    form = Triage()
    if form.validate_on_submit():
        return redirect(url_for(
            '.feedback',
            ticket_type=ticket_type,
            severe=form.severe.data
        ))
    return render_template(
        'views/support/triage.html',
        form=form,
        page_title={
            PROBLEM_TICKET_TYPE: 'Report a problem',
            GENERAL_TICKET_TYPE: 'Contact GOV.UK Notify support',
        }.get(ticket_type)
    )


@main.route('/support/<ticket_type:ticket_type>', methods=['GET', 'POST'])
def feedback(ticket_type):
    form = FeedbackOrProblem()

    if not form.feedback.data:
        form.feedback.data = session.pop('feedback_message', '')

    if request.args.get('severe') in ['yes', 'no']:
        severe = convert_to_boolean(request.args.get('severe'))
    else:
        severe = None

    out_of_hours_emergency = all((
        ticket_type != QUESTION_TICKET_TYPE,
        not in_business_hours(),
        severe,
    ))

    if needs_triage(ticket_type, severe):
        session['feedback_message'] = form.feedback.data
        return redirect(url_for('.triage', ticket_type=ticket_type))

    if needs_escalation(ticket_type, severe):
        return redirect(url_for('.bat_phone'))

    if current_user.is_authenticated:
        form.email_address.data = current_user.email_address
        form.name.data = current_user.name

    if form.validate_on_submit():
        user_email = form.email_address.data
        user_name = form.name.data or None
        if current_service:
            service_string = 'Service: "{name}"\n{url}\n'.format(
                name=current_service.name,
                url=url_for('main.service_dashboard', service_id=current_service.id, _external=True)
            )
        else:
            service_string = ''

        feedback_msg = '{}\n{}'.format(
            form.feedback.data,
            service_string,
        )

        ticket = zendesk_client.create_ticket(
            subject='Notify feedback',
            message=feedback_msg,
            ticket_type=ticket_type,
            p1=out_of_hours_emergency,
            user_email=user_email,
            user_name=user_name
        )
        current_app.logger.info(
            f'Created Zendesk ticket {ticket["id"]}'
        )
        return redirect(url_for(
            '.thanks',
            out_of_hours_emergency=out_of_hours_emergency,
            email_address_provided=(
                current_user.is_authenticated or bool(form.email_address.data)
            ),
        ))

    return render_template(
        'views/support/form.html',
        form=form,
        back_link=(
            url_for('.support')
            if severe is None else
            url_for('.triage', ticket_type=ticket_type)
        ),
        show_status_page_banner=(ticket_type == PROBLEM_TICKET_TYPE),
        page_title={
            GENERAL_TICKET_TYPE: 'Contact GOV.UK Notify support',
            PROBLEM_TICKET_TYPE: 'Report a problem',
            QUESTION_TICKET_TYPE: 'Ask a question or give feedback',
        }.get(ticket_type),
    )


@main.route('/support/escalate', methods=['GET', 'POST'])
def bat_phone():

    if current_user.is_authenticated:
        return redirect(url_for('main.feedback', ticket_type=PROBLEM_TICKET_TYPE))

    return render_template('views/support/bat-phone.html')


@main.route('/support/thanks', methods=['GET', 'POST'])
def thanks():
    return render_template(
        'views/support/thanks.html',
        out_of_hours_emergency=convert_to_boolean(request.args.get('out_of_hours_emergency')),
        email_address_provided=convert_to_boolean(request.args.get('email_address_provided')),
        out_of_hours=not in_business_hours(),
    )


def in_business_hours():

    now = datetime.utcnow().replace(tzinfo=pytz.utc)

    if is_weekend(now) or is_bank_holiday(now):
        return False

    return london_time_today_as_utc(9, 30) <= now < london_time_today_as_utc(17, 30)


def london_time_today_as_utc(hour, minute):
    return pytz.timezone('Europe/London').localize(
        datetime.now().replace(hour=hour, minute=minute)
    ).astimezone(pytz.utc)


def is_weekend(time):
    return time.strftime('%A') in {
        'Saturday',
        'Sunday',
    }


def is_bank_holiday(time):
    return bank_holidays.is_holiday(time.date())


def has_live_services(user_id):
    return any(
        service['restricted'] is False
        for service in service_api_client.get_services({'user_id': user_id})['data']
    )


def needs_triage(ticket_type, severe):
    return all((
        ticket_type != QUESTION_TICKET_TYPE,
        severe is None,
        (
            not current_user.is_authenticated or has_live_services(current_user.id)
        ),
        not in_business_hours(),
    ))


def needs_escalation(ticket_type, severe):
    return all((
        ticket_type != QUESTION_TICKET_TYPE,
        severe,
        not current_user.is_authenticated,
        not in_business_hours(),
    ))

from datetime import datetime

import pytz
from flask import redirect, render_template, request, session, url_for
from flask_login import current_user

from app import convert_to_boolean, current_service, service_api_client
from app.extensions import zendesk_client
from app.main import main
from app.main.forms import (
    FeedbackOrProblem,
    SupportRedirect,
    SupportType,
    Triage,
)

QUESTION_TICKET_TYPE = 'ask-question-give-feedback'
PROBLEM_TICKET_TYPE = "report-problem"


def get_prefilled_message():
    return {
        'agreement': (
            'Please can you tell me if there’s an agreement in place '
            'between GOV.UK Notify and my organisation?'
        ),
        'letter-branding': (
            'I would like my own logo on my letter templates.'
        ),
    }.get(
        request.args.get('body'), ''
    )


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
                    ticket_type=PROBLEM_TICKET_TYPE,
                ))

    return render_template('views/support/index.html', form=form)


@main.route('/support/public')
def support_public():
    return render_template('views/support/public.html')


@main.route('/support/triage', methods=['GET', 'POST'])
def triage():
    form = Triage()
    if form.validate_on_submit():
        return redirect(url_for(
            '.feedback',
            ticket_type=PROBLEM_TICKET_TYPE,
            severe=form.severe.data
        ))
    return render_template(
        'views/support/triage.html',
        form=form
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
        ticket_type == PROBLEM_TICKET_TYPE,
        not in_business_hours(),
        severe,
    ))

    if needs_triage(ticket_type, severe):
        session['feedback_message'] = form.feedback.data
        return redirect(url_for('.triage'))

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

        feedback_msg = '{}\n{}{}'.format(
            form.feedback.data,
            service_string,
            '' if user_email else '{} (no email address supplied)'.format(form.name.data)
        )

        zendesk_client.create_ticket(
            subject='Notify feedback',
            message=feedback_msg,
            ticket_type=ticket_type,
            p1=out_of_hours_emergency,
            user_email=user_email,
            user_name=user_name
        )
        return redirect(url_for(
            '.thanks',
            out_of_hours_emergency=out_of_hours_emergency,
            email_address_provided=(
                current_user.is_authenticated or bool(form.email_address.data)
            ),
        ))

    if not form.feedback.data:
        form.feedback.data = get_prefilled_message()

    return render_template(
        'views/support/form.html',
        form=form,
        is_problem=(ticket_type == PROBLEM_TICKET_TYPE),
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
    return time.strftime('%Y-%m-%d') in {
        # taken from https://www.gov.uk/bank-holidays.json
        # curl https://www.gov.uk/bank-holidays.json | jq '."england-and-wales".events[].date'
        "2016-01-01",
        "2016-03-25",
        "2016-03-28",
        "2016-05-02",
        "2016-05-30",
        "2016-08-29",
        "2016-12-26",
        "2016-12-27",
        "2017-01-02",
        "2017-04-14",
        "2017-04-17",
        "2017-05-01",
        "2017-05-29",
        "2017-08-28",
        "2017-12-25",
        "2017-12-26",
        "2018-01-01",
        "2018-03-30",
        "2018-04-02",
        "2018-05-07",
        "2018-05-28",
        "2018-08-27",
        "2018-12-25",
        "2018-12-26",
        "2019-01-01",
        "2019-04-19",
        "2019-04-22",
        "2019-05-06",
        "2019-05-27",
        "2019-08-26",
        "2019-12-25",
        "2019-12-26",
        "2020-01-01",
        "2020-04-10",
        "2020-04-13",
        "2020-05-08",
        "2020-05-25",
        "2020-08-31",
        "2020-12-25",
        "2020-12-28",
        "2021-01-01",
        "2021-04-02",
        "2021-04-05",
        "2021-05-03",
        "2021-05-31",
        "2021-08-30",
        "2021-12-27",
        "2021-12-28",
    }


def has_live_services(user_id):
    return any(
        service['restricted'] is False
        for service in service_api_client.get_services({'user_id': user_id})['data']
    )


def needs_triage(ticket_type, severe):
    return all((
        ticket_type == PROBLEM_TICKET_TYPE,
        severe is None,
        (
            not current_user.is_authenticated or has_live_services(current_user.id)
        ),
        not in_business_hours(),
    ))


def needs_escalation(ticket_type, severe):
    return all((
        ticket_type == PROBLEM_TICKET_TYPE,
        severe,
        not current_user.is_authenticated,
        not in_business_hours(),
    ))

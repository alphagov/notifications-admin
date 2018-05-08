from datetime import datetime

import pytz
from flask import abort, redirect, render_template, request, session, url_for
from flask_login import current_user

from app import (
    convert_to_boolean,
    current_service,
    service_api_client,
    zendesk_client,
)
from app.main import main
from app.main.forms import Feedback, Problem, SupportType, Triage

QUESTION_TICKET_TYPE = 'ask-question-give-feedback'
PROBLEM_TICKET_TYPE = "report-problem"


def get_prefilled_message():
    return {
        'agreement': (
            'Please can you tell me if there’s an agreement in place '
            'between GOV.UK Notify and my organisation?'
        ),
    }.get(
        request.args.get('body'), ''
    )


@main.route('/support', methods=['GET', 'POST'])
def support():
    form = SupportType()
    if form.validate_on_submit():
        return redirect(url_for(
            '.feedback',
            ticket_type=form.support_type.data,
        ))
    return render_template('views/support/index.html', form=form)


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


@main.route('/support/<ticket_type>', methods=['GET', 'POST'])
def feedback(ticket_type):
    try:
        form = {
            QUESTION_TICKET_TYPE: Feedback,
            PROBLEM_TICKET_TYPE: Problem,
        }[ticket_type]()
    except KeyError:
        abort(404)

    if not form.feedback.data:
        form.feedback.data = session.pop('feedback_message', '')

    if request.args.get('severe') in ['yes', 'no']:
        severe = convert_to_boolean(request.args.get('severe'))
    else:
        severe = None

    p1 = False
    urgent = False

    if in_business_hours():
        # if we're in the office, it's urgent (aka we'll get back in 30 mins)
        urgent = True
    elif ticket_type == PROBLEM_TICKET_TYPE and severe:
        # out of hours, it's only a p1 and it's only urgent if it's a p1
        urgent = True
        p1 = True

    anonymous = (
        (not form.email_address.data) and
        (not current_user.is_authenticated)
    )

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
            service_string = 'Service "{name}": {url}\n'.format(
                name=current_service['name'],
                url=url_for('main.service_dashboard', service_id=current_service['id'], _external=True)
            )
        else:
            service_string = ''

        feedback_msg = 'Environment: {}\n{}{}\n{}'.format(
            url_for('main.index', _external=True),
            service_string,
            '' if user_email else '{} (no email address supplied)'.format(form.name.data),
            form.feedback.data
        )

        zendesk_client.create_ticket(
            subject='Notify feedback',
            message=feedback_msg,
            ticket_type=ticket_type,
            p1=p1,
            user_email=user_email,
            user_name=user_name
        )
        return redirect(url_for('.thanks', urgent=urgent, anonymous=anonymous))

    if not form.feedback.data:
        form.feedback.data = get_prefilled_message()

    return render_template(
        'views/support/{}.html'.format(ticket_type),
        form=form,
        ticket_type=ticket_type,
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
        urgent=convert_to_boolean(request.args.get('urgent')),
        anonymous=convert_to_boolean(request.args.get('anonymous')),
        logged_in=current_user.is_authenticated,
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

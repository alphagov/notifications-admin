import requests
import pytz
from flask import render_template, url_for, redirect, flash, current_app, abort, request, session
from flask_login import current_user
from app import convert_to_boolean, current_service, service_api_client
from app.main import main
from app.main.forms import SupportType, Feedback, Problem, Triage
from datetime import datetime


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
            ticket_type='problem',
            severe=(form.severe.data == 'yes')
        ))
    return render_template(
        'views/support/triage.html',
        form=form
    )


@main.route('/support/submit/<ticket_type>', methods=['GET', 'POST'])
def feedback(ticket_type):

    try:
        form = {
            'question': Feedback,
            'problem': Problem,
        }[ticket_type]()
    except KeyError:
        abort(404)

    if not form.feedback.data:
        form.feedback.data = session.pop('feedback_message', '')

    if request.args.get('severe') in ['yes', 'no']:
        severe = convert_to_boolean(request.args.get('severe'))
    else:
        severe = None

    urgent = (
        in_business_hours() or
        (ticket_type == 'problem' and severe)
    )

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
        data = {
            'person_email': user_email or current_app.config.get('DESKPRO_PERSON_EMAIL'),
            'person_name': user_name,
            'department_id': current_app.config.get('DESKPRO_DEPT_ID'),
            'agent_team_id': current_app.config.get('DESKPRO_ASSIGNED_AGENT_TEAM_ID'),
            'subject': 'Notify feedback',
            'message': feedback_msg,
            'label': ticket_type,
            'urgency': 10 if urgent else 1,
        }
        headers = {
            "X-DeskPRO-API-Key": current_app.config.get('DESKPRO_API_KEY'),
            'Content-Type': "application/x-www-form-urlencoded"
        }
        resp = requests.post(
            current_app.config.get('DESKPRO_API_HOST') + '/api/tickets',
            data=data,
            headers=headers)
        if resp.status_code != 201:
            current_app.logger.error(
                "Deskpro create ticket request failed with {} '{}'".format(
                    resp.status_code,
                    resp.json())
                )
            abort(500, "Feedback submission failed")
        return redirect(url_for('.thanks', urgent=urgent, anonymous=anonymous))

    return render_template(
        'views/support/{}.html'.format(ticket_type),
        form=form,
        ticket_type=ticket_type,
    )


@main.route('/support/escalate', methods=['GET', 'POST'])
def bat_phone():

    if current_user.is_authenticated:
        return redirect(url_for('main.feedback', ticket_type='problem'))

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
    return time.strftime('%d/%m/%Y') in {
        # taken from
        # https://github.com/alphagov/calendars/blob/7f6512b0a95d77aa22accef105860074c19f1ec0/lib/data/bank-holidays.json
        "01/01/2016",
        "25/03/2016",
        "28/03/2016",
        "02/05/2016",
        "30/05/2016",
        "29/08/2016",
        "26/12/2016",
        "27/12/2016",
        "02/01/2017",
        "14/04/2017",
        "17/04/2017",
        "01/05/2017",
        "29/05/2017",
        "28/08/2017",
        "25/12/2017",
        "26/12/2017",
    }


def has_live_services(user_id):
    return any(
        service['restricted'] is False
        for service in service_api_client.get_services({'user_id': user_id})['data']
    )


def needs_triage(ticket_type, severe):
    return all((
        ticket_type == 'problem',
        severe is None,
        (
            not current_user.is_authenticated or has_live_services(current_user.id)
        ),
        not in_business_hours(),
    ))


def needs_escalation(ticket_type, severe):
    return all((
        ticket_type == 'problem',
        severe,
        not current_user.is_authenticated,
        not in_business_hours(),
    ))

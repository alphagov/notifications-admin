import requests
from flask import render_template, url_for, redirect, flash, current_app, abort
from app.main import main
from app.main.forms import Feedback


@main.route('/support', methods=['GET', 'POST'])
def support():
    return render_template('views/support/index.html')


@main.route('/support/feedback', methods=['GET', 'POST'])
def feedback():
    form = Feedback()
    if form.validate_on_submit():
        user_supplied_email = form.email_address.data != ''
        feedback_msg = 'Environment: {}\n{}\n{}'.format(
            url_for('main.index', _external=True),
            '' if user_supplied_email else '{} (no email address supplied)'.format(form.name.data),
            form.feedback.data
        )
        data = {
            'person_email': form.email_address.data or current_app.config.get('DESKPRO_PERSON_EMAIL'),
            'person_name': form.name.data or None,
            'department_id': current_app.config.get('DESKPRO_DEPT_ID'),
            'agent_team_id': current_app.config.get('DESKPRO_ASSIGNED_AGENT_TEAM_ID'),
            'subject': 'Notify feedback',
            'message': feedback_msg
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
        flash("Thanks, we’ve received your feedback", 'default_with_tick')
        return redirect(url_for('.support'))

    return render_template('views/support/feedback.html', form=form)

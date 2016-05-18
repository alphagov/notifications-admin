import requests
from flask import render_template, url_for, redirect, flash, current_app, abort
from app.main import main
from app.main.forms import Feedback


@main.route('/feedback', methods=['GET', 'POST'])
def feedback():
    form = Feedback()
    if form.validate_on_submit():
        data = {
            'person_email': current_app.config.get('DESKPRO_PERSON_EMAIL'),
            'department_id': current_app.config.get('DESKPRO_DEPT_ID'),
            'assigned_agent_team_id': current_app.config.get('DESKPRO_ASSIGNED_AGENT_TEAM_ID'),
            'subject': 'Notify feedback',
            'message': 'Environment: {}\n\n{}\n{}\n{}'.format(
                url_for('main.index', _external=True),
                form.name.data,
                form.email_address.data,
                form.feedback.data
            )
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
        flash("Your feedback has been submitted")
        return redirect(url_for('.feedback'))

    return render_template('views/feedback.html', form=form)

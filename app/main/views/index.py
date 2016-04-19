import markdown
import os
import requests
import json
from flask import (render_template, url_for, redirect, Markup, flash, current_app, abort)
from app.main import main
from flask_login import login_required
from app.main.forms import Feedback

from flask.ext.login import current_user
from mdx_gfm import GithubFlavoredMarkdownExtension


@main.route('/')
def index():
    if current_user and current_user.is_authenticated():
        return redirect(url_for('main.choose_service'))
    return render_template('views/signedout.html')


@main.route("/verify-mobile")
@login_required
def verify_mobile():
    return render_template('views/verify-mobile.html')


@main.route('/cookies')
def cookies():
    return render_template('views/cookies.html')


@main.route('/trial-mode')
def trial_mode():
    return render_template('views/trial-mode.html')


@main.route('/pricing')
def pricing():
    return render_template('views/pricing.html')


@main.route('/terms')
def terms():
    return render_template('views/terms-of-use.html')


@main.route('/feedback', methods=['GET', 'POST'])
def feedback():
    form = Feedback()
    if form.validate_on_submit():
        data = {
            'person_email': current_app.config.get('DESKPRO_PERSON_EMAIL'),
            'agent_team_id': current_app.config.get('DESKPRO_TEAM_ID'),
            'subject': 'Notify feedback',
            'message': '{}\n{}\n{}'.format(
                form.name.data,
                form.email_address.data,
                form.feedback.data)
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


@main.route('/documentation')
def documentation():
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(curr_dir, '../../../docs/index.md')) as source:
        return render_template(
            'views/documentation.html',
            body=Markup(markdown.markdown(
                source.read(),
                extensions=[GithubFlavoredMarkdownExtension()]
            ))
        )

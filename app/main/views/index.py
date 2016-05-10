import markdown
import os
from flask import (render_template, url_for, redirect, Markup)
from app.main import main
from flask_login import login_required

from flask.ext.login import current_user
from mdx_gfm import GithubFlavoredMarkdownExtension


@main.route('/')
def index():
    if current_user and current_user.is_authenticated:
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


@main.route('/documentation')
def documentation():
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(curr_dir, '../../../docs/index.md'), encoding='utf-8') as source:
        return render_template(
            'views/documentation.html',
            body=Markup(markdown.markdown(
                source.read(),
                extensions=[GithubFlavoredMarkdownExtension()]
            ))
        )

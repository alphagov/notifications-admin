from flask import render_template, url_for, redirect, jsonify
from app.main import main
from flask_login import login_required

from flask.ext.login import current_user


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

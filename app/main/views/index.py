from flask import render_template, url_for, redirect
from app.main import main
from flask_login import login_required

from flask.ext.login import current_user


@main.route('/')
def index():
    if current_user and current_user.is_authenticated():
        return redirect(url_for('main.choose_service'))
    return render_template('views/signedout.html')


@main.route("/register-from-invite")
@login_required
def register_from_invite():
    return render_template('views/register-from-invite.html')


@main.route("/verify-mobile")
@login_required
def verify_mobile():
    return render_template('views/verify-mobile.html')

from flask import (
    redirect,
    url_for,
    session
)

from flask.ext.login import logout_user

from app.main import main


@main.route('/sign-out', methods=(['GET']))
def sign_out():
    logout_user()
    session.clear()
    return redirect(url_for('main.sign_in'))

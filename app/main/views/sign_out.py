from flask import redirect, session, url_for
from flask_login import current_user, logout_user

from app.main import main


@main.route('/sign-out', methods=(['GET']))
def sign_out():
    current_user.sign_out()
    session.clear()
    logout_user()
    return redirect(url_for('main.index'))

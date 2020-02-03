from flask import redirect, url_for
from flask_login import current_user

from app.main import main


@main.route('/sign-out', methods=(['GET']))
def sign_out():
    current_user.sign_out()
    return redirect(url_for('main.index'))

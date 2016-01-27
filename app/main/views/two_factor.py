
from flask import (
    render_template, redirect, jsonify, session, url_for)

from flask_login import login_user

from app.main import main
from app.main.dao import users_dao
from app.main.forms import TwoFactorForm


@main.route('/two-factor', methods=['GET', 'POST'])
def two_factor():
    # TODO handle user_email not in session
    user_id = session['user_details']['id']

    def _check_code(code):
        return users_dao.check_verify_code(user_id, code, "sms")

    form = TwoFactorForm(_check_code)

    if form.validate_on_submit():
        user = users_dao.get_user_by_id(user_id)
        # Check if coming from new password page
        if 'password' in session['user_details']:
            user.set_password(session['user_details']['password'])
            users_dao.update_user(user)
        del session['user_details']
        login_user(user)
        return redirect(url_for('.choose_service'))

    return render_template('views/two-factor.html', form=form)

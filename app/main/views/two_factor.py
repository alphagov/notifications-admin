from flask import render_template, redirect, jsonify, session
from flask_login import login_user

from app.main import main
from app.main.dao import users_dao, verify_codes_dao
from app.main.forms import TwoFactorForm


@main.route("/two-factor", methods=['GET'])
def render_two_factor():
    return render_template('views/two-factor.html', form=TwoFactorForm())


@main.route('/two-factor', methods=['POST'])
def process_two_factor():
    form = TwoFactorForm()

    if form.validate_on_submit():
        user = users_dao.get_user_by_id(session['user_id'])
        verify_codes_dao.use_code_for_user_and_type(user_id=user.id, code_type='sms')
        login_user(user)
        return redirect('/dashboard')
    else:
        return jsonify(form.errors), 400

from flask import render_template, redirect, jsonify, session
from flask_login import login_user

from app.main import main
from app.main.dao import users_dao, verify_codes_dao
from app.main.forms import VerifyForm


@main.route('/verify', methods=['GET'])
def render_verify():
    return render_template('verify.html', form=VerifyForm())


@main.route('/verify', methods=['POST'])
def process_verify():
    form = VerifyForm()
    if form.validate_on_submit():
        user = users_dao.get_user_by_id(session['user_id'])
        verify_codes_dao.use_code_for_user_and_type(user_id=user.id, code_type='email')
        verify_codes_dao.use_code_for_user_and_type(user_id=user.id, code_type='sms')
        users_dao.activate_user(user.id)
        login_user(user)
        return redirect('/add-service')
    else:
        print(form.errors)
        return jsonify(form.errors), 400

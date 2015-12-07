from flask import render_template, redirect, jsonify, session
from flask_login import login_user

from app.main import main
from app.main.dao import users_dao
from app.main.encryption import checkpw
from app.main.forms import VerifyForm


@main.route('/verify', methods=['GET'])
def render_verify():
    return render_template('verify.html', form=VerifyForm())


@main.route('/verify', methods=['POST'])
def process_verify():
    form = VerifyForm()
    if form.validate_on_submit():
        valid_sms = checkpw(form.sms_code.data, session['sms_code'])
        valid_email = checkpw(form.email_code.data, session['email_code'])
        if valid_sms is False:
            return jsonify(sms_code='does not match'), 400
        if valid_email is False:
            return jsonify(email_code='does not match'), 400
    else:
        return jsonify(form.errors), 400

    user = users_dao.get_user_by_id(session['user_id'])
    users_dao.activate_user(user.id)
    login_user(user)

    return redirect('/add-service')

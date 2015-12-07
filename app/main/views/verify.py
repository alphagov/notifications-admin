from app.main import main
from flask import render_template, redirect, jsonify, session

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
            return jsonify(sms_code='invalid'), 400
        if valid_email is False:
            return jsonify(email_code='invalid'), 400
    else:
        return jsonify(form.errors), 400

    return redirect('/add-service')

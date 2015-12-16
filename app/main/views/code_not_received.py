from flask import render_template, redirect, jsonify, session

from app.main import main
from app.main.dao import users_dao, verify_codes_dao
from app.main.forms import EmailNotReceivedForm, TextNotReceivedForm
from app.main.views import send_sms_code, send_email_code


@main.route("/email-not-received", methods=['GET'])
def email_not_received():
    user = users_dao.get_user_by_id(session['user_id'])
    return render_template('views/email-not-received.html',
                           form=EmailNotReceivedForm(email_address=user.email_address))


@main.route('/email-not-received', methods=['POST'])
def check_and_resend_email_code():
    form = EmailNotReceivedForm()
    if form.validate_on_submit():
        user = users_dao.get_user_by_id(session['user_id'])
        users_dao.update_email_address(id=user.id, email_address=form.email_address.data)
        send_email_code(user_id=user.id, email=user.email_address)
        return redirect('/verify')
    return jsonify(form.errors), 400


@main.route("/text-not-received", methods=['GET'])
def text_not_received():
    user = users_dao.get_user_by_id(session['user_id'])
    return render_template('views/text-not-received.html', form=TextNotReceivedForm(mobile_number=user.mobile_number))


@main.route('/text-not-received', methods=['POST'])
def check_and_resend_text_code():
    form = TextNotReceivedForm()
    if form.validate_on_submit():
        user = users_dao.get_user_by_id(session['user_id'])
        users_dao.update_mobile_number(id=user.id, mobile_number=form.mobile_number.data)
        send_sms_code(user_id=user.id, mobile_number=user.mobile_number)
        return redirect('/verify')
    return jsonify(form.errors), 400

from flask import render_template

from app.main import main


@main.route("/email-not-received", methods=['GET'])
def email_not_received():
    return render_template('views/email-not-received.html')


@main.route('/email-not-received', methods=['POST'])
def check_and_resend_email_code():
    return None


@main.route("/text-not-received", methods=['GET'])
def text_not_received():
    return render_template('views/text-not-received.html')


@main.route('/text-not-received', methods=['POST'])
def check_and_resend_text_code():
    return None

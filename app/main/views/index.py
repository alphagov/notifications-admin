from flask import render_template
from app.main import main
from flask_login import login_required


@main.route('/')
def index():
    return render_template('views/signedout.html')


@main.route("/register-from-invite")
@login_required
def registerfrominvite():
    return render_template('views/register-from-invite.html')


@main.route("/verify-mobile")
@login_required
def verifymobile():
    return render_template('views/verify-mobile.html')


@main.route("/services/<int:service_id>/send-email")
@login_required
def sendemail(service_id):
    return render_template('views/send-email.html')


@main.route("/services/<int:service_id>/check-email")
@login_required
def checkemail(service_id):
    return render_template('views/check-email.html')


@main.route("/services/<int:service_id>/manage-users")
@login_required
def manageusers(service_id):
    return render_template('views/manage-users.html', service_id=service_id)


@main.route("/services/<int:service_id>/api-keys")
@login_required
def apikeys(service_id):
    return render_template('views/api-keys.html', service_id=service_id)

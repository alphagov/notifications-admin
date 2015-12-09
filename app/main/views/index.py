from flask import render_template
from flask_login import login_required

from app.main import main


@main.route('/')
def index():
    return render_template('signedout.html')


@main.route("/govuk")
def govuk():
    return render_template('govuk_template.html')


@main.route("/register-from-invite")
def registerfrominvite():
    return render_template('register-from-invite.html')


@main.route("/verify-mobile")
def verifymobile():
    return render_template('verify-mobile.html')


@main.route("/text-not-received-2")
def textnotreceived2():
    return render_template('text-not-received-2.html')


@main.route("/dashboard")
@login_required
def dashboard():
    return render_template('dashboard.html')


@main.route("/add-service")
@login_required
def addservice():
    return render_template('add-service.html')


@main.route("/send-sms")
def sendsms():
    return render_template('send-sms.html')


@main.route("/check-sms")
def checksms():
    return render_template('check-sms.html')


@main.route("/email-not-received")
def emailnotreceived():
    return render_template('email-not-received.html')


@main.route("/text-not-received")
def textnotreceived():
    return render_template('text-not-received.html')


@main.route("/send-email")
def sendemail():
    return render_template('send-email.html')


@main.route("/check-email")
def checkemail():
    return render_template('check-email.html')


@main.route("/jobs")
def showjobs():
    return render_template('jobs.html')


@main.route("/jobs/job")
def showjob():
    return render_template('job.html')


@main.route("/jobs/job/notification")
def shownotification():
    return render_template('notification.html')


@main.route("/forgot-password")
def forgotpassword():
    return render_template('forgot-password.html')


@main.route("/new-password")
def newpassword():
    return render_template('new-password.html')


@main.route("/user-profile")
def userprofile():
    return render_template('user-profile.html')


@main.route("/manage-users")
def manageusers():
    return render_template('manage-users.html')


@main.route("/service-settings")
def servicesettings():
    return render_template('service-settings.html')


@main.route("/api-keys")
def apikeys():
    return render_template('api-keys.html')


@main.route("/verification-not-received")
def verificationnotreceived():
    return render_template('verification-not-received.html')


@main.route("/manage-templates")
def managetemplates():
    return render_template('manage-templates.html')


@main.route("/edit-template")
def edittemplate():
    return render_template('edit-template.html')

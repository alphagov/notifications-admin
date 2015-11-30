from flask import render_template

from app.main import main


@main.route('/')
def index():
    return render_template('signedout.html')


@main.route("/govuk")
def govuk():
    return render_template('govuk_template.html')


@main.route("/hello-world")
def helloworld():
    return render_template('hello-world.html')


@main.route("/register")
def register():
    return render_template('register.html')


@main.route("/register-from-invite")
def registerfrominvite():
    return render_template('register-from-invite.html')


@main.route("/verify")
def verify():
    return render_template('verify.html')


@main.route("/verify-mobile")
def verifymobile():
    return render_template('verify-mobile.html')


@main.route("/dashboard")
def dashboard():
    return render_template('dashboard.html')


@main.route("/sign-in")
def signin():
    return render_template('signin.html')


@main.route("/add-service")
def addservice():
    return render_template('add-service.html')


@main.route("/two-factor")
def twofactor():
    return render_template('two-factor.html')


@main.route("/send-sms")
def sendsms():
    return render_template('send_sms.html')


@main.route("/check-sms")
def checksms():
    return render_template('check_sms.html')


@main.route("/email-not-received")
def emailnotreceived():
    return render_template('email-not-received.html')


@main.route("/text-not-received")
def textnotreceived():
    return render_template('text-not-received.html')


@main.route("/send-email")
def sendemail():
    return render_template('send_email.html')


@main.route("/check-email")
def checkemail():
    return render_template('check_email.html')


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

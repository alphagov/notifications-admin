from flask import render_template

from app.main import main


@main.route('/')
def index():
    return render_template('signedout.html')


@main.route("/govuk")
def govuk():
    return render_template('govuk_template.html')


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
    return render_template('send-sms.html')


@main.route("/check-sms")
def checksms():
    return render_template('check-sms.html')


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

from flask import request, render_template, redirect, url_for
from flask.ext.login import current_user
from app.main import main
from app.main.forms import (
    ChangePasswordForm, ChangeNameForm, ChangeEmailForm, ConfirmEmailForm,
    ChangeMobileNumberForm, ConfirmMobileNumberForm, ConfirmPasswordForm
)


@main.route("/user-profile")
def userprofile():
    return render_template('views/user-profile.html')


@main.route("/user-profile/name", methods=['GET', 'POST'])
def userprofile_name():

    form = ChangeNameForm()

    if request.method == 'GET':
        if current_user.is_authenticated():
            form.new_name.data = current_user.name
        return render_template(
            'views/user-profile/change.html',
            thing='name',
            form_field=form.new_name
        )
    elif request.method == 'POST':
        return redirect(url_for('.userprofile'))


@main.route("/user-profile/email", methods=['GET', 'POST'])
def userprofile_email():

    form = ChangeEmailForm()

    if request.method == 'GET':
        if current_user.is_authenticated():
            form.email_address.data = current_user.email_address
        return render_template(
            'views/user-profile/change.html',
            thing='email address',
            form_field=form.email_address
        )
    elif request.method == 'POST':
        return redirect(url_for('.userprofile_email_authenticate'))


@main.route("/user-profile/email/authenticate", methods=['GET', 'POST'])
def userprofile_email_authenticate():

    form = ConfirmPasswordForm()

    if request.method == 'GET':
        return render_template(
            'views/user-profile/authenticate.html',
            thing='email address',
            form=form,
            back_link=url_for('.userprofile_email')
        )
    elif request.method == 'POST':
        return redirect(url_for('.userprofile_email_confirm'))


@main.route("/user-profile/email/confirm", methods=['GET', 'POST'])
def userprofile_email_confirm():

    form = ConfirmEmailForm()

    if request.method == 'GET':
        return render_template(
            'views/user-profile/confirm.html',
            form_field=form.email_code,
            thing='email address'
        )
    elif request.method == 'POST':
        return redirect(url_for('.userprofile'))


@main.route("/user-profile/mobile-number", methods=['GET', 'POST'])
def userprofile_mobile_number():

    form = ChangeMobileNumberForm()

    if request.method == 'GET':
        if current_user.is_authenticated():
            form.mobile_number.data = current_user.mobile_number
        return render_template(
            'views/user-profile/change.html',
            thing='mobile number',
            form_field=form.mobile_number
        )
    elif request.method == 'POST':
        return redirect(url_for('.userprofile_mobile_number_authenticate'))


@main.route("/user-profile/mobile-number/authenticate", methods=['GET', 'POST'])
def userprofile_mobile_number_authenticate():

    form = ConfirmPasswordForm()

    if request.method == 'GET':
        return render_template(
            'views/user-profile/authenticate.html',
            thing='mobile number',
            form=form,
            back_link=url_for('.userprofile_mobile_number_confirm')
        )
    elif request.method == 'POST':
        return redirect(url_for('.userprofile_mobile_number_confirm'))


@main.route("/user-profile/mobile-number/confirm", methods=['GET', 'POST'])
def userprofile_mobile_number_confirm():

    form = ConfirmMobileNumberForm()

    if request.method == 'GET':
        return render_template(
            'views/user-profile/confirm.html',
            form_field=form.sms_code,
            thing='mobile number'
        )
    elif request.method == 'POST':
        return redirect(url_for('.userprofile'))


@main.route("/user-profile/password", methods=['GET', 'POST'])
def userprofile_password():

    form = ChangePasswordForm()

    if request.method == 'GET':
        return render_template(
            'views/user-profile/change-password.html',
            form=form
        )
    elif request.method == 'POST':
        return redirect(url_for('.userprofile'))

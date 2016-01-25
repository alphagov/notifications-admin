from flask import (
    request, render_template, redirect, url_for, session)
from flask.ext.login import current_user
from app.main import main
from app.main.dao.users_dao import (verify_password, update_user)
from app.main.forms import (
    ChangePasswordForm, ChangeNameForm, ChangeEmailForm, ConfirmEmailForm,
    ChangeMobileNumberForm, ConfirmMobileNumberForm, ConfirmPasswordForm
)

NEW_EMAIL = 'new-email'
NEW_MOBILE = 'new-mob'
NEW_EMAIL_PASSWORD_CONFIRMED = 'new-email-password-confirmed'
NEW_MOBILE_PASSWORD_CONFIRMED = 'new-mob-password-confirmed'


@main.route("/user-profile")
def user_profile():
    return render_template('views/user-profile.html')


@main.route("/user-profile/name", methods=['GET', 'POST'])
def user_profile_name():

    form = ChangeNameForm(new_name=current_user.name)

    if form.validate_on_submit():
        current_user.name = form.new_name
        update_user(current_user)
        return redirect(url_for('.user_profile'))

    return render_template(
        'views/user-profile/change.html',
        thing='name',
        form_field=form.new_name
    )


@main.route("/user-profile/email", methods=['GET', 'POST'])
def user_profile_email():

    form = ChangeEmailForm(email_address=current_user.email_address)

    if form.validate_on_submit():
        session[NEW_EMAIL] = form.email_address.data
        return redirect(url_for('.user_profile_email_authenticate'))
    return render_template(
        'views/user-profile/change.html',
        thing='email address',
        form_field=form.email_address
    )


@main.route("/user-profile/email/authenticate", methods=['GET', 'POST'])
def user_profile_email_authenticate():

    # Validate password for form
    def _check_password(pwd):
        return verify_password(current_user, pwd)
    form = ConfirmPasswordForm(_check_password)

    if NEW_EMAIL not in session:
        return redirect('main.user_profile_email')

    if form.validate_on_submit():
        session[NEW_EMAIL_PASSWORD_CONFIRMED] = True
        return redirect(url_for('.user_profile_email_confirm'))

    return render_template(
        'views/user-profile/authenticate.html',
        thing='email address',
        form=form,
        back_link=url_for('.user_profile_email')
    )


@main.route("/user-profile/email/confirm", methods=['GET', 'POST'])
def user_profile_email_confirm():

    # TODO add verify code support
    form = ConfirmEmailForm()

    if NEW_EMAIL_PASSWORD_CONFIRMED not in session:
        return redirect('main.user_profile_email_authenticate')

    if form.validate_on_submit():
        del session[NEW_EMAIL]
        del session[NEW_EMAIL_PASSWORD_CONFIRMED]
        current_user.email_address = session['new_email']
        update_user(current_user)
        return redirect(url_for('.user_profile'))

    return render_template(
        'views/user-profile/confirm.html',
        form_field=form.email_code,
        thing='email address'
    )


@main.route("/user-profile/mobile-number", methods=['GET', 'POST'])
def user_profile_mobile_number():

    form = ChangeMobileNumberForm(mobile_number=current_user.mobile_number)

    if form.validate_on_submit():
        session[NEW_MOBILE] = form.mobile_number.data
        return redirect(url_for('.user_profile_mobile_number_authenticate'))

    return render_template(
        'views/user-profile/change.html',
        thing='mobile number',
        form_field=form.mobile_number
    )


@main.route("/user-profile/mobile-number/authenticate", methods=['GET', 'POST'])
def user_profile_mobile_number_authenticate():

    # Validate password for form
    def _check_password(pwd):
        return verify_password(current_user, pwd)
    form = ConfirmPasswordForm(_check_password)

    if NEW_MOBILE not in session:
        return redirect(url_for('.user_profile_mobile_number'))

    if form.validate_on_submit():
        session[NEW_MOBILE_PASSWORD_CONFIRMED] = True
        return redirect(url_for('.user_profile_mobile_number_confirm'))

    return render_template(
        'views/user-profile/authenticate.html',
        thing='mobile number',
        form=form,
        back_link=url_for('.user_profile_mobile_number_confirm')
    )


@main.route("/user-profile/mobile-number/confirm", methods=['GET', 'POST'])
def user_profile_mobile_number_confirm():

    form = ConfirmMobileNumberForm()

    if form.validate_on_submit():
        del session[NEW_MOBILE]
        del session[NEW_MOBILE_PASSWORD_CONFIRMED]
        current_user.mobile_user
        update_user(current_user)
        return redirect(url_for('.user_profile'))

    return render_template(
        'views/user-profile/confirm.html',
        form_field=form.sms_code,
        thing='mobile number'
    )


@main.route("/user-profile/password", methods=['GET', 'POST'])
def user_profile_password():

    form = ChangePasswordForm()

    if form.validate_on_submit():
        return redirect(url_for('.user_profile'))

    return render_template(
        'views/user-profile/change-password.html',
        form=form
    )

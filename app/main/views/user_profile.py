from flask import (
    render_template,
    redirect,
    url_for,
    session
)

from flask.ext.login import current_user
from flask_login import login_required
from app.main import main

from app.main.forms import (
    ChangePasswordForm,
    ChangeNameForm,
    ChangeEmailForm,
    ConfirmEmailForm,
    ChangeMobileNumberForm,
    ConfirmMobileNumberForm,
    ConfirmPasswordForm
)

from app import user_api_client

NEW_EMAIL = 'new-email'
NEW_MOBILE = 'new-mob'
NEW_EMAIL_PASSWORD_CONFIRMED = 'new-email-password-confirmed'
NEW_MOBILE_PASSWORD_CONFIRMED = 'new-mob-password-confirmed'


@main.route("/user-profile")
@login_required
def user_profile():
    return render_template('views/user-profile.html')


@main.route("/user-profile/name", methods=['GET', 'POST'])
@login_required
def user_profile_name():

    form = ChangeNameForm(new_name=current_user.name)

    if form.validate_on_submit():
        current_user.name = form.new_name.data
        user_api_client.update_user(current_user)
        return redirect(url_for('.user_profile'))

    return render_template(
        'views/user-profile/change.html',
        thing='name',
        form_field=form.new_name
    )


@main.route("/user-profile/email", methods=['GET', 'POST'])
@login_required
def user_profile_email():

    def _is_email_unique(email):
        return user_api_client.is_email_unique(email)
    form = ChangeEmailForm(_is_email_unique,
                           email_address=current_user.email_address)

    if form.validate_on_submit():
        session[NEW_EMAIL] = form.email_address.data
        return redirect(url_for('.user_profile_email_authenticate'))
    return render_template(
        'views/user-profile/change.html',
        thing='email address',
        form_field=form.email_address
    )


@main.route("/user-profile/email/authenticate", methods=['GET', 'POST'])
@login_required
def user_profile_email_authenticate():
    # Validate password for form
    def _check_password(pwd):
        return user_api_client.verify_password(current_user.id, pwd)
    form = ConfirmPasswordForm(_check_password)

    if NEW_EMAIL not in session:
        return redirect('main.user_profile_email')

    if form.validate_on_submit():
        session[NEW_EMAIL_PASSWORD_CONFIRMED] = True
        user_api_client.send_verify_code(current_user.id, 'email', session[NEW_EMAIL])
        return redirect(url_for('.user_profile_email_confirm'))

    return render_template(
        'views/user-profile/authenticate.html',
        thing='email address',
        form=form,
        back_link=url_for('.user_profile_email')
    )


@main.route("/user-profile/email/confirm", methods=['GET', 'POST'])
@login_required
def user_profile_email_confirm():

    # Validate verify code for form
    def _check_code(cde):
        return user_api_client.check_verify_code(current_user.id, cde, 'email')
    form = ConfirmEmailForm(_check_code)

    if NEW_EMAIL_PASSWORD_CONFIRMED not in session:
        return redirect('main.user_profile_email_authenticate')

    if form.validate_on_submit():
        current_user.email_address = session[NEW_EMAIL]
        del session[NEW_EMAIL]
        del session[NEW_EMAIL_PASSWORD_CONFIRMED]
        user_api_client.update_user(current_user)
        return redirect(url_for('.user_profile'))

    return render_template(
        'views/user-profile/confirm.html',
        form_field=form.email_code,
        thing='email address'
    )


@main.route("/user-profile/mobile-number", methods=['GET', 'POST'])
@login_required
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
@login_required
def user_profile_mobile_number_authenticate():

    # Validate password for form
    def _check_password(pwd):
        return user_api_client.verify_password(current_user.id, pwd)
    form = ConfirmPasswordForm(_check_password)

    if NEW_MOBILE not in session:
        return redirect(url_for('.user_profile_mobile_number'))

    if form.validate_on_submit():
        session[NEW_MOBILE_PASSWORD_CONFIRMED] = True
        user_api_client.send_verify_code(current_user.id, 'sms', session[NEW_MOBILE])
        return redirect(url_for('.user_profile_mobile_number_confirm'))

    return render_template(
        'views/user-profile/authenticate.html',
        thing='mobile number',
        form=form,
        back_link=url_for('.user_profile_mobile_number_confirm')
    )


@main.route("/user-profile/mobile-number/confirm", methods=['GET', 'POST'])
@login_required
def user_profile_mobile_number_confirm():

    # Validate verify code for form
    def _check_code(cde):
        return user_api_client.check_verify_code(current_user.id, cde, 'sms')

    if NEW_MOBILE_PASSWORD_CONFIRMED not in session:
        return redirect(url_for('.user_profile_mobile_number'))

    form = ConfirmMobileNumberForm(_check_code)

    if form.validate_on_submit():
        current_user.mobile_number = session[NEW_MOBILE]
        del session[NEW_MOBILE]
        del session[NEW_MOBILE_PASSWORD_CONFIRMED]
        user_api_client.update_user(current_user)
        return redirect(url_for('.user_profile'))

    return render_template(
        'views/user-profile/confirm.html',
        form_field=form.sms_code,
        thing='mobile number'
    )


@main.route("/user-profile/password", methods=['GET', 'POST'])
@login_required
def user_profile_password():

    # Validate password for form
    def _check_password(pwd):
        return user_api_client.verify_password(current_user.id, pwd)
    form = ChangePasswordForm(_check_password)

    if form.validate_on_submit():
        current_user.set_password(form.new_password.data)
        user_api_client.update_user(current_user)
        return redirect(url_for('.user_profile'))

    return render_template(
        'views/user-profile/change-password.html',
        form=form
    )

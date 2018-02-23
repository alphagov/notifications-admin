import json

from flask import (
    abort,
    render_template,
    redirect,
    url_for,
    session,
    current_app)

from flask_login import login_required, current_user
from notifications_utils.url_safe_token import check_token

from app.main import main

from app.main.forms import (
    ChangePasswordForm,
    ChangeNameForm,
    ChangeEmailForm,
    ChangeMobileNumberForm,
    ConfirmMobileNumberForm,
    ConfirmPasswordForm
)

from app.utils import is_gov_user

from app import user_api_client

NEW_EMAIL = 'new-email'
NEW_MOBILE = 'new-mob'
NEW_MOBILE_PASSWORD_CONFIRMED = 'new-mob-password-confirmed'


@main.route("/user-profile")
@login_required
def user_profile():
    return render_template(
        'views/user-profile.html',
        can_see_edit=is_gov_user(current_user.email_address)
    )


@main.route("/user-profile/name", methods=['GET', 'POST'])
@login_required
def user_profile_name():

    form = ChangeNameForm(new_name=current_user.name)

    if form.validate_on_submit():
        user_api_client.update_user_attribute(current_user.id, name=form.new_name.data)
        return redirect(url_for('.user_profile'))

    return render_template(
        'views/user-profile/change.html',
        thing='name',
        form_field=form.new_name
    )


@main.route("/user-profile/email", methods=['GET', 'POST'])
@login_required
def user_profile_email():

    if not is_gov_user(current_user.email_address):
        abort(403)

    def _is_email_already_in_use(email):
        return user_api_client.is_email_already_in_use(email)
    form = ChangeEmailForm(_is_email_already_in_use,
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
        user_api_client.send_change_email_verification(current_user.id, session[NEW_EMAIL])
        return render_template('views/change-email-continue.html',
                               new_email=session[NEW_EMAIL])

    return render_template(
        'views/user-profile/authenticate.html',
        thing='email address',
        form=form,
        back_link=url_for('.user_profile_email')
    )


@main.route("/user-profile/email/confirm/<token>", methods=['GET'])
@login_required
def user_profile_email_confirm(token):
    token_data = check_token(token,
                             current_app.config['SECRET_KEY'],
                             current_app.config['DANGEROUS_SALT'],
                             current_app.config['EMAIL_EXPIRY_SECONDS'])
    token_data = json.loads(token_data)
    user_id = token_data['user_id']
    new_email = token_data['email']
    user_api_client.update_user_attribute(user_id, email_address=new_email)
    session.pop(NEW_EMAIL, None)

    return redirect(url_for('.user_profile'))


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
        user = user_api_client.get_user(current_user.id)
        # the user will have a new current_session_id set by the API - store it in the cookie for future requests
        session['current_session_id'] = user.current_session_id
        mobile_number = session[NEW_MOBILE]
        del session[NEW_MOBILE]
        del session[NEW_MOBILE_PASSWORD_CONFIRMED]
        user_api_client.update_user_attribute(current_user.id, mobile_number=mobile_number)
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
        user_api_client.update_password(current_user.id, password=form.new_password.data)
        return redirect(url_for('.user_profile'))

    return render_template(
        'views/user-profile/change-password.html',
        form=form
    )

from flask import (
    Markup,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user

from app import invite_api_client, login_manager, user_api_client
from app.main import main
from app.main.forms import LoginForm


@main.route('/sign-in', methods=(['GET', 'POST']))
def sign_in():
    if current_user and current_user.is_authenticated:
        return redirect(url_for('main.show_accounts_or_dashboard'))

    form = LoginForm()

    if form.validate_on_submit():

        user = user_api_client.get_user_by_email_or_none(form.email_address.data)
        user = _get_and_verify_user(user, form.password.data)
        if user and user.state == 'pending':
            return redirect(url_for('main.resend_email_verification'))

        if user and session.get('invited_user'):
            invited_user = session.get('invited_user')
            if user.email_address.lower() != invited_user['email_address'].lower():
                flash("You can't accept an invite for another person.")
                session.pop('invited_user', None)
                abort(403)
            else:
                invite_api_client.accept_invite(invited_user['service'], invited_user['id'])
        if user:
            session['user_details'] = {"email": user.email_address, "id": user.id}
            if user.is_active:
                if user.auth_type == "email_auth":
                    return sign_in_email(user.id, user.email_address)
                else:
                    return sign_in_sms(user.id, user.mobile_number)

        # Vague error message for login in case of user not known, locked, inactive or password not verified
        flash(Markup(
            (
                "The email address or password you entered is incorrect."
                " <a href={password_reset}>Forgot your password</a>?"
            ).format(password_reset=url_for('.forgot_password'))
        ))

    other_device = current_user.logged_in_elsewhere()
    return render_template(
        'views/signin.html',
        form=form,
        again=bool(request.args.get('next')),
        other_device=other_device
    )


def sign_in_email(user_id, to):
    if request.args.get('next'):
        user_api_client.send_verify_code(user_id, 'email', None, request.args.get('next'))
    else:
        user_api_client.send_verify_code(user_id, 'email', None)
    return redirect(url_for('.two_factor_email_sent'))


def sign_in_sms(user_id, to):
    user_api_client.send_verify_code(user_id, 'sms', to)
    if request.args.get('next'):
        return redirect(url_for('.two_factor', next=request.args.get('next')))
    else:
        return redirect(url_for('.two_factor'))


@login_manager.unauthorized_handler
def sign_in_again():
    return redirect(
        url_for('main.sign_in', next=request.path)
    )


def _get_and_verify_user(user, password):
    if not user:
        return None
    elif user.is_locked():
        return None
    elif not user_api_client.verify_password(user.id, password):
        return None
    else:
        return user

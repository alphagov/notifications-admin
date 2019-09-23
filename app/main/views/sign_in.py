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

from app import login_manager
from app.main import main
from app.main.forms import LoginForm
from app.models.user import InvitedUser, User


@main.route('/sign-in', methods=(['GET', 'POST']))
def sign_in():
    if current_user and current_user.is_authenticated:
        return redirect(url_for('main.show_accounts_or_dashboard'))

    form = LoginForm()

    if form.validate_on_submit():

        user = User.from_email_address_and_password_or_none(
            form.email_address.data, form.password.data
        )

        if user and user.state == 'pending':
            return redirect(url_for('main.resend_email_verification'))

        if user and session.get('invited_user'):
            invited_user = InvitedUser.from_session()
            if user.email_address.lower() != invited_user.email_address.lower():
                flash("You cannot accept an invite for another person.")
                session.pop('invited_user', None)
                abort(403)
            else:
                invited_user.accept_invite()
        if user and user.sign_in():
            if user.sms_auth:
                return redirect(url_for('.two_factor', next=request.args.get('next')))
            if user.email_auth:
                return redirect(url_for('.two_factor_email_sent'))

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


@login_manager.unauthorized_handler
def sign_in_again():
    return redirect(
        url_for('main.sign_in', next=request.path)
    )

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
from app.utils import hide_from_search_engines
from app.utils.login import is_safe_redirect_url


@main.route('/sign-in', methods=(['GET', 'POST']))
@hide_from_search_engines
def sign_in():
    redirect_url = request.args.get('next')
    if current_user and current_user.is_authenticated:
        if redirect_url and is_safe_redirect_url(redirect_url):
            return redirect(redirect_url)
        return redirect(url_for('main.show_accounts_or_dashboard'))

    form = LoginForm()
    password_reset_url = url_for('.forgot_password', next=request.args.get('next'))

    if form.validate_on_submit():

        user = User.from_email_address_and_password_or_none(
            form.email_address.data, form.password.data
        )

        if user:
            # add user to session to mark us as in the process of signing the user in
            session['user_details'] = {"email": user.email_address, "id": user.id}

            if user.state == 'pending':
                return redirect(url_for('main.resend_email_verification', next=redirect_url))

            if user.is_active:
                if session.get('invited_user_id'):
                    invited_user = InvitedUser.from_session()
                    if user.email_address.lower() != invited_user.email_address.lower():
                        flash("You cannot accept an invite for another person.")
                        session.pop('invited_user_id', None)
                        abort(403)
                    else:
                        invited_user.accept_invite()

                user.send_login_code()

                if user.sms_auth:
                    return redirect(url_for('.two_factor_sms', next=redirect_url))
                if user.email_auth:
                    return redirect(url_for('.two_factor_email_sent', next=redirect_url))
                if user.webauthn_auth:
                    return redirect(url_for('.two_factor_webauthn', next=redirect_url))

        # Vague error message for login in case of user not known, locked, inactive or password not verified
        flash(Markup(
            (
                f"The email address or password you entered is incorrect."
                f"&ensp;<a href={password_reset_url} class='govuk-link'>Forgotten your password?</a>"
            )
        ))

    other_device = current_user.logged_in_elsewhere()
    return render_template(
        'views/signin.html',
        form=form,
        again=bool(redirect_url),
        other_device=other_device,
        password_reset_url=password_reset_url
    )


@login_manager.unauthorized_handler
def sign_in_again():
    return redirect(
        url_for('main.sign_in', next=request.path)
    )

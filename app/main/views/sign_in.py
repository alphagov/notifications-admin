from flask import (
    render_template,
    redirect,
    url_for,
    session,
    flash,
    request
)

from flask.ext.login import (
    current_user,
    login_fresh,
    confirm_login
)

from app.main import main
from app.main.dao import services_dao

from app import user_api_client


from app.main.forms import LoginForm


@main.route('/sign-in', methods=(['GET', 'POST']))
def sign_in():
    if current_user and current_user.is_authenticated():
        return redirect(url_for('main.choose_service'))

    form = LoginForm()
    if form.validate_on_submit():
        user = user_api_client.get_user_by_email_or_none(form.email_address.data)
        user = _get_and_verify_user(user, form.password.data)
        if user and user.state == 'pending':
            flash("You haven't verified your email or mobile number yet.")
            return redirect(url_for('main.sign_in'))
        if user:
            # Remember me login
            if not login_fresh() and \
               not current_user.is_anonymous() and \
               current_user.id == user.id and \
               user.is_active():
                confirm_login()
                services = services_dao.get_services(user.id).get('data', [])
                if (len(services) == 1):
                    return redirect(url_for('main.service_dashboard', service_id=services[0]['id']))
                else:
                    return redirect(url_for('main.choose_service'))

            session['user_details'] = {"email": user.email_address, "id": user.id}
            if user.is_active():
                user_api_client.send_verify_code(user.id, 'sms', user.mobile_number)
                if request.args.get('next'):
                    return redirect(url_for('.two_factor', next=request.args.get('next')))
                else:
                    return redirect(url_for('.two_factor'))
        # Vague error message for login in case of user not known, locked, inactive or password not verified
        flash('Username or password is incorrect')

    invited_user = session.get('invited_user')
    if invited_user:
        message = 'You already have an account with GOV.UK Notify. Sign in to your account to accept this invitation.'
        flash(message, 'default')

    return render_template('views/signin.html', form=form)


def _get_and_verify_user(user, password):
    if not user:
        return None
    elif user.is_locked():
        return None
    elif not user_api_client.verify_password(user.id, password):
        return None
    else:
        return user

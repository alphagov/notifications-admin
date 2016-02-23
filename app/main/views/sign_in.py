from flask import (
    render_template,
    redirect,
    url_for,
    session,
    abort,
    flash
)

from flask.ext.login import (current_user, login_fresh, confirm_login)

from app.main import main
from app.main.dao import (users_dao, services_dao)
from app.main.forms import LoginForm


@main.route('/sign-in', methods=(['GET', 'POST']))
def sign_in():
    if current_user and current_user.is_authenticated():
        return redirect(url_for('main.choose_service'))

    form = LoginForm()
    if form.validate_on_submit():
        user = users_dao.get_user_by_email(form.email_address.data)
        user = _get_and_verify_user(user, form.password.data)
        if user:
            # If the current user is using a remember me token
            # and needs the session just needs to be refreshed.
            # If the login credentials are correct
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
            if user.state == 'pending':
                return redirect(url_for('.verify'))
            elif user.is_active():
                users_dao.send_verify_code(user.id, 'sms', user.mobile_number)
                return redirect(url_for('.two_factor'))
        # Vague error message for login in case of user not known, locked, inactive or password not verified
        flash('Username or password is incorrect')

    return render_template('views/signin.html', form=form)


def _get_and_verify_user(user, password):
    if not user:
        return None
    elif user.is_locked():
        return None
    elif not users_dao.verify_password(user.id, password):
        return None
    else:
        return user

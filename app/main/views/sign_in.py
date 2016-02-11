from flask import (
    render_template,
    redirect,
    url_for,
    session,
    abort,
    flash
)

from flask.ext.login import current_user

from app.main import main
from app.main.dao import users_dao
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
            session['user_details'] = {"email": user.email_address, "id": user.id}
            if user.state == 'pending':
                return redirect(url_for('.verify'))
            elif user.is_active():
                users_dao.send_verify_code(user.id, 'sms')
                return redirect(url_for('.two_factor'))
        # Vague error message for login in case of user not known, locked, inactive or password not verified
        flash('Username or password is incorrect')

    return render_template('views/signin.html', form=form)


def _get_and_verify_user(user, password):
    print(user.serialize())
    print(password)
    if not user:
        return None
    elif user.is_locked():
        return None
    elif not users_dao.verify_password(user.id, password):
        return None
    else:
        return user

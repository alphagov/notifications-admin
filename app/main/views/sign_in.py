from flask import (
    render_template,
    redirect,
    url_for,
    session,
    abort
)


from flask.ext.login import current_user


from app.main import main
from app.main.dao import users_dao
from app.main.forms import LoginForm
from app.notify_client.sender import send_sms_code


@main.route('/sign-in', methods=(['GET', 'POST']))
def sign_in():
    if current_user and current_user.is_authenticated():
        return redirect(url_for('main.choose_service'))
    try:
        form = LoginForm()
        if form.validate_on_submit():
            user = _get_and_verify_user(form.email_address.data, form.password.data)
            if user:
                send_sms_code(user.id, user.mobile_number)
                session['user_email'] = user.email_address
                return redirect(url_for('.two_factor'))
            else:
                # Vague error message for login in case of user not known, locked, inactive or password not verified
                form.password.errors.append('Username or password is incorrect')

        return render_template('views/signin.html', form=form)
    except:
        import traceback
        traceback.print_exc()
        abort(500)


def _get_and_verify_user(email_address, password):
    user = users_dao.get_user_by_email(email_address)
    if not user:
        return None
    elif user.is_locked():
        return None
    elif not user.is_active():
        return None
    elif not users_dao.verify_password(user, password):
        return None
    else:
        return user

from flask import (
    render_template, redirect, jsonify, url_for)
from flask import session

from app.main import main
from app.main.dao import users_dao
from app.main.encryption import check_hash
from app.main.forms import LoginForm
from app.main.views import send_sms_code


@main.route('/sign-in', methods=(['GET', 'POST']))
def sign_in():
    form = LoginForm()
    if form.validate_on_submit():
        user = users_dao.get_user_by_email(form.email_address.data)
        if user:
            if not user.is_locked() and user.is_active() and check_hash(form.password.data, user.password):
                send_sms_code(user.id, user.mobile_number)
                session['user_id'] = user.id
                return redirect(url_for('.two_factor'))
            else:
                users_dao.increment_failed_login_count(user.id)
        # Vague error message for login
        form.password.errors.append('Username or password is incorrect')

    return render_template('views/signin.html', form=form)

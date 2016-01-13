
from flask import (
    render_template, redirect, jsonify, session, url_for)

from flask_login import login_user

from app.main import main
from app.main.dao import users_dao, verify_codes_dao
from app.main.forms import TwoFactorForm


@main.route('/two-factor', methods=['GET', 'POST'])
def two_factor():
    # TODO handle user_email not in session
    user = users_dao.get_user_by_email(session['user_email'])
    codes = verify_codes_dao.get_codes(user.id)
    form = TwoFactorForm(codes)

    if form.validate_on_submit():
        verify_codes_dao.use_code_for_user_and_type(user_id=user.id, code_type='sms')
        login_user(user)
        return redirect(url_for('.dashboard', service_id=123))

    return render_template('views/two-factor.html', form=form)

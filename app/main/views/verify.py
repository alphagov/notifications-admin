from flask import (
    render_template, redirect, jsonify, session, url_for)
from flask_login import login_user

from app.main import main
from app.main.dao import users_dao, verify_codes_dao
from app.main.forms import VerifyForm


@main.route('/verify', methods=['GET', 'POST'])
def verify():
    # TODO there needs to be a way to regenerate a session id
    try:
        user = users_dao.get_user_by_id(session['user_id'])
        form = VerifyForm()
        if form.validate_on_submit():
            verify_codes_dao.use_code_for_user_and_type(user_id=user.id, code_type='email')
            verify_codes_dao.use_code_for_user_and_type(user_id=user.id, code_type='sms')
            users_dao.activate_user(user.id)
            login_user(user)
            return redirect(url_for('.add_service'))
        return render_template('views/verify.html', form=form)
    except:
        import traceback
        traceback.print_exc()

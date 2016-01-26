from flask import (
    render_template,
    redirect,
    session,
    url_for,
    abort
)

from client.errors import HTTPError

from flask_login import login_user

from app.main import main
from app.main.dao import users_dao, verify_codes_dao
from app.main.forms import VerifyForm


@main.route('/verify', methods=['GET', 'POST'])
def verify():
    # TODO there needs to be a way to regenerate a session id
    # or handle gracefully.
    user_id = session['user_details']['id']
    codes = verify_codes_dao.get_codes(user_id)
    form = VerifyForm(codes)

    if form.validate_on_submit():
        verify_codes_dao.use_code_for_user_and_type(user_id=user_id, code_type='email')
        verify_codes_dao.use_code_for_user_and_type(user_id=user_id, code_type='sms')

        try:
            user = users_dao.get_user_by_id(user_id)
            activated_user = users_dao.activate_user(user)
            login_user(activated_user)
            return redirect(url_for('main.add_service', first='first'))
        except HTTPError as e:
            if e.status_code == 404:
                abort(404)
            else:
                raise e

    return render_template('views/verify.html', form=form)

from flask import (
    render_template,
    redirect,
    session,
    url_for
)

from flask_login import login_user

from app.main import main
from app.main.dao import users_dao
from app.main.forms import VerifyForm


@main.route('/verify', methods=['GET', 'POST'])
def verify():

    # TODO there needs to be a way to regenerate a session id
    # or handle gracefully.
    user_id = session['user_details']['id']

    def _check_code(code, code_type):
        return users_dao.check_verify_code(user_id, code, code_type)
    form = VerifyForm(_check_code)
    if form.validate_on_submit():
        try:
            user = users_dao.get_user_by_id(user_id)
            activated_user = users_dao.activate_user(user)
            login_user(activated_user)
            return redirect(url_for('main.add_service', first='first'))
        finally:
            del session['user_details']

    return render_template('views/verify.html', form=form)


from flask import (
    render_template,
    redirect,
    session,
    url_for
)

from flask_login import login_user

from app.main import main
from app.main.dao import users_dao, services_dao
from app.main.forms import TwoFactorForm


@main.route('/two-factor', methods=['GET', 'POST'])
def two_factor():
    # TODO handle user_email not in session
    try:
        user_id = session['user_details']['id']
    except KeyError:
        return redirect('main.sign_in')

    def _check_code(code):
        return users_dao.check_verify_code(user_id, code, "sms")

    form = TwoFactorForm(_check_code)

    if form.validate_on_submit():
        try:
            user = users_dao.get_user_by_id(user_id)
            services = services_dao.get_services(user_id).get('data', [])
            # Check if coming from new password page
            if 'password' in session['user_details']:
                user.set_password(session['user_details']['password'])
                users_dao.update_user(user)
            login_user(user, remember=True)
        finally:
            del session['user_details']
        if len(services) == 1:
            return redirect(url_for('main.service_dashboard', service_id=services[0]['id']))
        else:
            return redirect(url_for('main.choose_service'))

    return render_template('views/two-factor.html', form=form)

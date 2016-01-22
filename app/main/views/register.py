from datetime import datetime, timedelta

from flask import (
    render_template,
    redirect,
    session,
    abort,
    url_for
)

from flask.ext.login import current_user

from client.errors import HTTPError

from app.main import main
from app.main.dao import users_dao
from app.main.forms import RegisterUserForm

from app import user_api_client

# TODO how do we handle duplicate unverifed email addresses?
# malicious or otherwise.
from app.notify_client.sender import send_sms_code, send_email_code


@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user and current_user.is_authenticated():
        return redirect(url_for('main.choose_service'))

    form = RegisterUserForm(users_dao.get_user_by_email)

    if form.validate_on_submit():
        try:
            user = user_api_client.register_user(form.name.data,
                                                 form.email_address.data,
                                                 form.mobile_number.data,
                                                 form.password.data)
        except HTTPError as e:
            if e.status_code == 404:
                abort(404)
            else:
                raise e

        # TODO possibly there should be some exception handling
        # for sending sms and email codes.
        # How do we report to the user there is a problem with
        # sending codes apart from service unavailable?
        # at the moment i believe http 500 is fine.
        send_sms_code(user_id=user.id, mobile_number=user.mobile_number)
        send_email_code(user_id=user.id, email=user.email_address)
        session['expiry_date'] = str(datetime.now() + timedelta(hours=1))
        session['user_details'] = {"email": user.email_address, "id": user.id}
        return redirect('/verify')

    return render_template('views/register.html', form=form)

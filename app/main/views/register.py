from datetime import datetime, timedelta

from flask import (
    render_template,
    redirect,
    session,
    current_app,
    abort
)

from client.errors import HTTPError

from app.main import main
from app.models import User
from app.main.dao import users_dao
from app.main.forms import RegisterUserForm

from app.notify_client.user_api_client import UserApiClient

# TODO how do we handle duplicate unverifed email addresses?
# malicious or otherwise.
from app.notify_client.sender import send_sms_code, send_email_code


@main.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterUserForm(users_dao.get_user_by_email)

    if form.validate_on_submit():

        #  TODO remove once all api integrations done
        user = User(name=form.name.data,
                    email_address=form.email_address.data,
                    mobile_number=form.mobile_number.data,
                    password=form.password.data,
                    created_at=datetime.now(),
                    role_id=1)
        users_dao.insert_user(user)

        user_api_client = UserApiClient(current_app.config['API_HOST_NAME'],
                                        current_app.config['ADMIN_CLIENT_USER_NAME'],
                                        current_app.config['ADMIN_CLIENT_SECRET'])
        try:
            user_api_client.register_user(form.name.data,
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
        send_sms_code(user_id=user.id, mobile_number=form.mobile_number.data)
        send_email_code(user_id=user.id, email=form.email_address.data)
        session['expiry_date'] = str(datetime.now() + timedelta(hours=1))
        session['user_email'] = user.email_address
        return redirect('/verify')

    return render_template('views/register.html', form=form)

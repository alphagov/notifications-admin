from datetime import datetime, timedelta

from flask import render_template, redirect, jsonify, session
from sqlalchemy.exc import SQLAlchemyError

from app.main import main
from app.main.dao import users_dao
from app.main.encryption import hashpw
from app.main.exceptions import AdminApiClientException
from app.main.forms import RegisterUserForm
from app.main.views import send_sms_code, send_email_code
from app.models import User


# TODO how do we handle duplicate unverifed email addresses?
# malicious or otherwise.
@main.route('/register', methods=['GET', 'POST'])
def process_register():
    try:
        existing_emails, existing_mobiles = zip(
            *[(x.email_address, x.mobile_number) for x in
                users_dao.get_all_users()])
    except ValueError:
        # Value error is raised if the db is empty.
        existing_emails, existing_mobiles = [], []

    form = RegisterUserForm(existing_emails, existing_mobiles)

    if form.validate_on_submit():
        user = User(name=form.name.data,
                    email_address=form.email_address.data,
                    mobile_number=form.mobile_number.data,
                    password=form.password.data,
                    created_at=datetime.now(),
                    role_id=1)
        users_dao.insert_user(user)
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

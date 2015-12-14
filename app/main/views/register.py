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


@main.route("/register", methods=['GET'])
def render_register():
    return render_template('views/register.html', form=RegisterUserForm())


@main.route('/register', methods=['POST'])
def process_register():
    form = RegisterUserForm()

    if form.validate_on_submit():
        user = User(name=form.name.data,
                    email_address=form.email_address.data,
                    mobile_number=form.mobile_number.data,
                    password=form.password.data,
                    created_at=datetime.now(),
                    role_id=1)
        try:
            users_dao.insert_user(user)
            send_sms_code(user_id=user.id, mobile_number=form.mobile_number.data)
            send_email_code(user_id=user.id, email=form.email_address.data)
            session['expiry_date'] = str(datetime.now() + timedelta(hours=1))
            session['user_id'] = user.id
        except AdminApiClientException as e:
            return jsonify(admin_api_client_error=e.value)
        except SQLAlchemyError:
            return jsonify(database_error='encountered database error'), 400
    else:
        return jsonify(form.errors), 400
    return redirect('/verify')

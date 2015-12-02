from datetime import datetime

from flask import render_template, redirect, jsonify

from app.main import main
from app.main.dao import users_dao
from app.main.forms import RegisterUserForm
from app.models import User


@main.route("/register", methods=['GET'])
def render_register():
    return render_template('register.html', form=RegisterUserForm())


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
            return redirect('/two-factor')
        except Exception as e:
            return jsonify(database_error='encountered database error'), 400
    else:
        return jsonify(form.errors), 400

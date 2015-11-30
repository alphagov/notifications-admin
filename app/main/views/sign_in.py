from datetime import datetime

from flask import render_template, redirect, jsonify
from flask_login import login_user

from app.main import main
from app.main.forms import LoginForm
from app.main.dao import users_dao
from app.models import User
from app.main.encryption import checkpw


@main.route("/sign-in", methods=(['GET']))
def render_sign_in():
    return render_template('signin.html', form=LoginForm())


@main.route('/sign-in', methods=(['POST']))
def process_sign_in():
    form = LoginForm()
    if form.validate_on_submit():
        user = users_dao.get_user_by_email(form.email_address.data)
        if user.is_locked():
            return jsonify(locked_out=True), 401
        if user is None:
            return jsonify(authorization=False), 401
        if checkpw(form.password.data, user.password):
            login_user(user)
        else:
            users_dao.increment_failed_login_count(user.id)
            return jsonify(authorization=False), 401
    else:
        return jsonify(form.errors), 400
    return redirect('/two-factor')


@main.route('/temp-create-users', methods=(['GET']))
def render_create_user():
    return render_template('temp-create-users.html', form=LoginForm())


@main.route('/temp-create-users', methods=(['POST']))
def create_user_for_test():
    form = LoginForm()
    if form.validate_on_submit():
        user = User(email_address=form.email_address.data,
                    name=form.email_address.data,
                    password=form.password.data,
                    created_at=datetime.now(),
                    mobile_number='+447651234534',
                    role_id=1)
        users_dao.insert_user(user)

        return redirect('/sign-in')
    else:
        print(form.errors)
        return redirect(form.errors), 400

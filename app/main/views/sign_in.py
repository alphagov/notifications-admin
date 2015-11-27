from datetime import datetime

from flask import render_template, redirect, url_for, jsonify
from flask_login import login_user

from app.main import main
from app.main.forms import LoginForm
from app.main.dao import users_dao
from app.models import Users
from app.main.encryption import encrypt


@main.route("/sign-in", methods=(['GET']))
def render_sign_in():
    return render_template('signin.html', form=LoginForm())


@main.route('/sign-in', methods=(['POST']))
def process_sign_in():
    form = LoginForm()
    if form.validate_on_submit():
        user = users_dao.get_user_by_email(form.email_address)
        if user is None:
            return jsonify(authorization=False), 404
        if user.password == encrypt(form.password):
            login_user(user)
        else:
            return jsonify(authorization=False), 404

    return redirect('/two-factor')


@main.route('/create_user', methods=(['POST']))
def create_user_for_test():
    form = LoginForm()
    user = Users(email_address=form.email_address,
                 name=form.email_address,
                 password=form.password,
                 created_at=datetime.now(),
                 role_id=1)
    users_dao.insert_user(user)

    return 'created'

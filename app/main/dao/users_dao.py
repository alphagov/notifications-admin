from datetime import datetime

from sqlalchemy.orm import load_only

from app import db, login_manager
from app.models import User
from app.main.encryption import hashpw


@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)


def insert_user(user):
    user.password = hashpw(user.password)
    db.session.add(user)
    db.session.commit()


# TODO Would be better to have a generic get and update for user
# something that replicates the sql functionality.
def get_user_by_id(id):
    return User.query.filter_by(id=id).first()


def get_all_users():
    return User.query.all()


def get_user_by_email(email_address):
    return User.query.filter_by(email_address=email_address).first()


def increment_failed_login_count(id):
    user = User.query.filter_by(id=id).first()
    user.failed_login_count += 1
    db.session.commit()


def activate_user(id):
    user = get_user_by_id(id)
    user.state = 'active'
    db.session.add(user)
    db.session.commit()


def update_email_address(id, email_address):
    user = get_user_by_id(id)
    user.email_address = email_address
    db.session.add(user)
    db.session.commit()


def update_mobile_number(id, mobile_number):
    user = get_user_by_id(id)
    user.mobile_number = mobile_number
    db.session.add(user)
    db.session.commit()


def update_password(id, password):
    user = get_user_by_id(id)
    user.password = hashpw(password)
    user.password_changed_at = datetime.now()
    db.session.add(user)
    db.session.commit()


def find_all_email_address():
    return [x.email_address for x in User.query.options(load_only("email_address")).all()]

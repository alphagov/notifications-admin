from datetime import datetime

from sqlalchemy.orm import load_only

from app import db, login_manager
from app.models import User
from app.main.encryption import hashpw

from app import user_api_client


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
    return user_api_client.get_user(id)


def get_all_users():
    return user_api_client.get_users()


def get_user_by_email(email_address):
    return user_api_client.get_user_by_email(email_address)


def verify_password(user, password):
    return user_api_client.verify_password(user, password)


def increment_failed_login_count(id):
    user = get_user_by_id(id)
    user.failed_login_count += 1


def activate_user(user):
    user.state = 'active'
    return user_api_client.update_user(user)


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


def update_password(user, password):
    user.password = hashpw(password)
    user.password_changed_at = datetime.now()
    user.state = 'active'
    db.session.add(user)
    db.session.commit()


def request_password_reset(email):
    user = get_user_by_email(email)
    user.state = 'request_password_reset'
    db.session.add(user)
    db.session.commit()

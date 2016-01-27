from datetime import datetime

from sqlalchemy.orm import load_only

from app import login_manager
from app.main.encryption import hashpw

from app import user_api_client


@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)


# TODO Would be better to have a generic get and update for user
# something that replicates the sql functionality.
def get_user_by_id(id):
    return user_api_client.get_user(id)


def get_all_users():
    return user_api_client.get_users()


def get_user_by_email(email_address):
    return user_api_client.get_user_by_email(email_address)


def verify_password(user_id, password):
    return user_api_client.verify_password(user_id, password)


def update_user(user):
    return user_api_client.update_user(user)


def increment_failed_login_count(id):
    user = get_user_by_id(id)
    user.failed_login_count += 1
    return user_api_client.update_user(user)


def activate_user(user):
    user.state = 'active'
    return user_api_client.update_user(user)


def is_email_unique(email_address):
    if user_api_client.get_user_by_email(email_address):
        return False
    return True


def request_password_reset(email):
    user = get_user_by_email(email)
    user.state = 'request_password_reset'
    # TODO update user


def send_verify_code(user_id, code_type, to=None):
    return user_api_client.send_verify_code(user_id, code_type)


def check_verify_code(user_id, code, code_type):
    return user_api_client.check_verify_code(user_id, code, code_type)

from app import db
from app.models import Users
from app.main.encryption import encrypt


def insert_user(user):
    user.password = encrypt(user.password)
    db.session.add(user)
    db.session.commit()


def get_user_by_id(id):
    return Users.query.filter_by(id=id).first()


def get_all_users():
    return Users.query.all()


def get_user_by_email(email_address):
    return Users.query.filter_by(email_address=email_address).first()
